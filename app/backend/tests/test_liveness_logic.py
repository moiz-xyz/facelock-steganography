"""Liveness decision logic on synthetic landmark signals (no images needed)."""
from facelock.liveness import ChallengeBook, FrameObs, count_blinks, evaluate


def seq(ears, yaws=None):
    yaws = yaws or [0.5] * len(ears)
    return [FrameObs(1, e, y) for e, y in zip(ears, yaws)]


OPEN, SHUT = 0.28, 0.10


def test_count_blinks():
    ears = [OPEN] * 5 + [SHUT] * 2 + [OPEN] * 5 + [SHUT] + [OPEN] * 3
    assert count_blinks(ears, OPEN, 0.62) == 2
    assert count_blinks([OPEN] * 20, OPEN, 0.62) == 0
    assert count_blinks([SHUT] * 3 + [OPEN] * 10, OPEN, 0.62) == 0   # starting closed is not a blink


def test_static_photo_fails():
    r = evaluate(seq([0.27] * 30), "blink_twice")
    assert not r.passed and "static" in r.reason


def test_blink_twice():
    ears = [OPEN] * 6 + [SHUT] * 2 + [OPEN] * 6 + [SHUT] * 2 + [OPEN] * 6
    assert evaluate(seq(ears), "blink_twice").passed
    one = [OPEN] * 10 + [SHUT] * 2 + [OPEN] * 10
    r = evaluate(seq(one), "blink_twice")
    assert not r.passed and "2 blinks" in r.reason


def test_turn_direction_must_match():
    ears = [OPEN] * 4 + [SHUT] * 2 + [OPEN] * 20
    yaws = [0.5] * 10 + [0.55, 0.6, 0.66, 0.7, 0.66, 0.6, 0.55] + [0.5] * 9
    assert evaluate(seq(ears, yaws), "turn_left").passed
    r = evaluate(seq(ears, yaws), "turn_right")
    assert not r.passed and "right" in r.reason


def test_multiple_faces_rejected():
    obs = seq([OPEN] * 20)
    obs[5] = FrameObs(2)
    assert "more than one" in evaluate(obs, "blink_twice").reason


def test_face_missing_rejected():
    obs = seq([OPEN] * 5) + [FrameObs(0)] * 20
    assert "visible" in evaluate(obs, "blink_twice").reason


def test_challenges_single_use():
    book = ChallengeBook(ttl_s=60)
    c = book.issue()
    assert c["type"] in ("blink_twice", "turn_left", "turn_right")
    assert book.consume(c["challenge_id"]) == c["type"]
    assert book.consume(c["challenge_id"]) is None


def test_blink_seen_by_blendshape_when_ear_barely_changes():
    """Glasses / looking down: EAR dips only ~15 %, but the blink blendshape jumps."""
    ears = [0.20] * 8 + [0.175] * 2 + [0.20] * 8 + [0.172] * 2 + [0.20] * 8
    scores = [0.28] * 8 + [0.72] * 2 + [0.28] * 8 + [0.68] * 2 + [0.28] * 8
    obs = [FrameObs(1, e, 0.5 + 0.002 * (i % 3), b) for i, (e, b) in enumerate(zip(ears, scores))]
    assert count_blinks(ears, 0.20, 0.62) == 0                  # EAR alone misses it
    r = evaluate(obs, "blink_twice")
    assert r.blinks == 2 and r.passed


def test_constant_blendshape_is_not_a_blink():
    ears = [0.20 + 0.004 * (i % 2) for i in range(30)]
    obs = [FrameObs(1, e, 0.5 + 0.004 * (i % 3), 0.30) for i, e in enumerate(ears)]
    r = evaluate(obs, "blink_twice")
    assert r.blinks == 0 and not r.passed
