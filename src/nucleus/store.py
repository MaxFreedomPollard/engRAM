"""In-memory SQLite store (invariant I2: the database only ever exists in RAM).

The whole database image is serialized into the sealed vault payload.
Record text is additionally encrypted with a per-record key (crypto-shred);
FTS5 rows and freed pages are removed with DELETE + VACUUM on shred so the
serialized image genuinely no longer contains the content.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid

import numpy as np

from . import crypto
from .crypto import CryptoError

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    ikey INTEGER UNIQUE,            -- integer key for the vector index
    ns TEXT NOT NULL,
    ct BLOB NOT NULL,               -- AEAD(record_key, JSON{text})
    key_wrapped BLOB NOT NULL,      -- AEAD(master_key, record_key); destroyed on shred
    vec BLOB NOT NULL,              -- float32 embedding
    dim INTEGER NOT NULL,
    tags TEXT NOT NULL,             -- JSON list
    importance REAL NOT NULL,
    quarantined INTEGER NOT NULL,
    pack TEXT,                      -- pack name for pack records, NULL for organic
    prov TEXT NOT NULL,             -- JSON {host, agent, session}
    created REAL NOT NULL,
    accessed REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(id UNINDEXED, text);
CREATE TABLE IF NOT EXISTS audit (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    caller TEXT NOT NULL,
    op TEXT NOT NULL,
    detail TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


class StoreError(CryptoError):
    pass


class Store:
    def __init__(self, image: bytes | None = None):
        # Autocommit: the DB lives only in RAM — durability comes from the
        # vault's own AEAD journal, and VACUUM (crypto-shred) needs no open tx.
        self.conn = sqlite3.connect(":memory:", isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        if image is not None:
            self.conn.deserialize(image)
        else:
            self.conn.executescript(SCHEMA)
        try:
            self.conn.execute("SELECT count(*) FROM fts")
        except sqlite3.OperationalError as exc:
            raise StoreError(
                "This Python's SQLite lacks FTS5, which Nucleus requires "
                "for hybrid search. Install a Python built with full SQLite."
            ) from exc

    def serialize(self) -> bytes:
        return self.conn.serialize()

    # -- records ------------------------------------------------------------

    def next_ikey(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(ikey), 0) + 1 AS n FROM records").fetchone()
        return int(row["n"])

    def insert(self, *, record_id: str | None, ns: str, text: str, vec: np.ndarray,
               tags: list[str], importance: float, quarantined: bool, pack: str | None,
               prov: dict, master_key: bytes, created: float | None = None) -> str:
        rid = record_id or uuid.uuid4().hex
        rk, wrapped = crypto.new_record_key(master_key, rid)
        ct = crypto.seal(rk, crypto.canonical_json({"text": text}),
                         aad=b"nucleus-record-body:" + rid.encode())
        now = time.time()
        self.conn.execute(
            "INSERT INTO records (id, ikey, ns, ct, key_wrapped, vec, dim, tags, importance,"
            " quarantined, pack, prov, created, accessed)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, self.next_ikey(), ns, ct, wrapped,
             vec.astype(np.float32).tobytes(), int(vec.shape[0]),
             json.dumps(tags), float(importance), int(quarantined), pack,
             json.dumps(prov), created or now, now),
        )
        self.conn.execute("INSERT INTO fts (id, text) VALUES (?, ?)", (rid, text))
        return rid

    def get_row(self, record_id: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()

    def decrypt_text(self, row: sqlite3.Row, master_key: bytes) -> str:
        rk = crypto.unwrap_record_key(master_key, row["id"], row["key_wrapped"])
        body = crypto.unseal(rk, row["ct"], aad=b"nucleus-record-body:" + row["id"].encode())
        return json.loads(body)["text"]

    def delete(self, record_id: str, shred: bool) -> bool:
        """Delete a record. shred=True also VACUUMs so the content (including
        FTS tokens and freed pages) is gone from the next serialized image,
        and the per-record key is destroyed with the row."""
        cur = self.conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        self.conn.execute("DELETE FROM fts WHERE id = ?", (record_id,))
        if cur.rowcount == 0:
            return False
        if shred:
            self.conn.execute("VACUUM")
        return True

    def touch(self, record_id: str) -> None:
        self.conn.execute("UPDATE records SET accessed = ? WHERE id = ?",
                          (time.time(), record_id))

    def all_vectors(self) -> tuple[list[str], list[int], np.ndarray]:
        rows = self.conn.execute("SELECT id, ikey, vec, dim FROM records ORDER BY ikey").fetchall()
        ids = [r["id"] for r in rows]
        ikeys = [r["ikey"] for r in rows]
        if not rows:
            return ids, ikeys, np.zeros((0, 0), dtype=np.float32)
        mat = np.vstack([np.frombuffer(r["vec"], dtype=np.float32) for r in rows])
        return ids, ikeys, mat

    def count(self, ns: str | None = None) -> int:
        if ns is None:
            return self.conn.execute("SELECT COUNT(*) c FROM records").fetchone()["c"]
        return self.conn.execute("SELECT COUNT(*) c FROM records WHERE ns = ?", (ns,)).fetchone()["c"]

    def namespaces(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT ns, COUNT(*) c FROM records GROUP BY ns ORDER BY ns").fetchall()
        return [{"namespace": r["ns"], "records": r["c"]} for r in rows]

    def fts_search(self, query: str, limit: int) -> list[tuple[str, float]]:
        """BM25 keyword search. Returns (id, rank) best-first."""
        safe = " ".join(
            '"' + t.replace('"', "") + '"' for t in query.split() if t.replace('"', "")
        )
        if not safe:
            return []
        rows = self.conn.execute(
            "SELECT id, rank FROM fts WHERE fts MATCH ? ORDER BY rank LIMIT ?",
            (safe, limit),
        ).fetchall()
        return [(r["id"], float(r["rank"])) for r in rows]

    # -- meta ---------------------------------------------------------------

    def get_meta(self, k: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT v FROM meta WHERE k = ?", (k,)).fetchone()
        return row["v"] if row else default

    def set_meta(self, k: str, v: str) -> None:
        self.conn.execute(
            "INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
            (k, v),
        )
