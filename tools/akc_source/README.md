# AKC source (build-time only, gitignored)

Place the Artificial Knowledge Collection 6.0 raw JSONL files here to rebuild
`akc-pragmatic.mpack`. Expected files (from the repo
MaxFreedomPollard/artificial-knowledge-collection-6.0):

- measure-of-things/measure-of-things.jsonl
- physical-constants/constants.jsonl
- world-factbook/world-factbook.jsonl
- world-factbook/world-physical-features.jsonl
- sky-and-elements/sky-and-elements.jsonl
- nutrition/nutrition.jsonl

Either keep the repo's subdir/file layout, or drop them here flat. Then:

    python tools/build_akc_pack.py 1.0.0 --akc-dir tools/akc_source

Only the built, signed `src/nucleus/data/akc-pragmatic.mpack` ships in the
package — these raw sources are not committed.
