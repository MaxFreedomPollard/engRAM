"""The write-decision function: what becomes a memory and why."""
from nucleus import salience


def test_bare_acknowledgements_not_stored():
    for msg in ("ok", "Thanks!", "sounds good", "continue", "y", "got it"):
        v = salience.assess_turn(msg, "Sure — done.")
        assert not v.store, msg


def test_short_noise_not_stored():
    assert not salience.assess_turn("hm right", "Indeed.").store


def test_substantive_turn_stored_at_default_importance():
    v = salience.assess_turn(
        "Walk me through how the QC reconciliation spreadsheet is structured",
        "It has three tabs...")
    assert v.store and v.importance == salience.DEFAULT_IMPORTANCE
    assert not v.has_signal  # → caller applies the novelty gate


def test_durability_signals_force_store_and_raise_importance():
    cases = [
        "Remember that the office door code changed",
        "I always take Fridays off",
        "My timezone is Eastern",
        "never deploy on weekends",
        "The deadline is due by the 25th",
        "ok",  # bare ack, but paired with a signal answer below
    ]
    answers = ["Noted."] * 5 + ["Noted — I'll always use tabs from now on."]
    for msg, ans in zip(cases, answers):
        v = salience.assess_turn(msg, ans)
        assert v.store and v.has_signal, msg
        assert v.importance == salience.SIGNAL_IMPORTANCE


def test_signal_skips_novelty_gate_flag():
    v = salience.assess_turn("Remember my badge number", "Saved.")
    assert v.has_signal  # caller must NOT novelty-filter explicit asks


def test_empty_turn():
    assert not salience.assess_turn("", "Some assistant text").store


def test_novelty_threshold_sits_between_topical_and_duplicate():
    assert 0.9 <= salience.NOVELTY_THRESHOLD < 0.97
