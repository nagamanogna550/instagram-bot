import os
import random
import tempfile
from datetime import datetime

from bot import InstagramBot
from captions import (MAX_HASHTAGS, build_hashtags, clean_hashtag, draft_caption,
                      pick_comment, validate_caption)
from safety import MIN_DELAY, RateLimiter, human_delay, in_active_hours
from session import run_session


def expect_error(exc, fn, *args, **kw):
    try:
        fn(*args, **kw)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


def tmp():
    return os.path.join(tempfile.mkdtemp(), "log.json")


def test_rate_limiter():
    path = tmp()
    rl = RateLimiter({"like": 2}, path=path)
    rl.record("like"); rl.record("like")
    assert not rl.can_do("like") and rl.remaining("like") == 0
    expect_error(RuntimeError, rl.record, "like")
    expect_error(ValueError, rl.can_do, "teleport")
    assert RateLimiter({"like": 2}, path=path).used("like") == 2      # persisted

    day = {"d": "2026-10-01"}                                         # new day resets
    rl2 = RateLimiter({"like": 1}, path=tmp(), today=lambda: day["d"])
    rl2.record("like")
    day["d"] = "2026-10-02"
    assert rl2.can_do("like")


def test_delays_and_hours():
    slept = []
    for _ in range(300):
        d = human_delay(4, 8, sleep=slept.append, rng=random)
        assert 4 <= d <= 8 + 8 * 3
    assert min(slept) >= 4
    expect_error(ValueError, human_delay, MIN_DELAY - 1, 5)
    expect_error(ValueError, human_delay, 10, 5)
    assert in_active_hours(9, 22, datetime(2026, 1, 1, 10))
    assert not in_active_hours(9, 22, datetime(2026, 1, 1, 3))


def test_captions():
    assert clean_hashtag("Street Food!") == "#streetfood" and clean_hashtag("!!!") == ""
    assert build_hashtags(["a", "A", "b"]) == ["#a", "#b"]
    assert len(build_hashtags([f"t{i}" for i in range(100)], limit=99)) <= MAX_HASHTAGS
    cap = draft_caption("Sunset at the beach", "playful", ["sunset", "beach"], rng=random.Random(1))
    assert "#sunset" in cap and "Sunset at the beach" in cap
    expect_error(ValueError, draft_caption, "  ")
    expect_error(ValueError, draft_caption, "x", "angry")
    expect_error(ValueError, validate_caption, "a" * 2201)
    expect_error(ValueError, validate_caption, " ".join(f"#t{i}" for i in range(31)))
    assert pick_comment({"x"}, random.Random(1)) != "x"


def test_dry_run_session_and_limits():
    bot = InstagramBot("u", "p", dry_run=True, limiter=RateLimiter(path=tmp()), sleep=lambda s: None)
    bot.start(); assert bot.login()
    s = run_session(bot, "#travel", likes=5, comments=2, follows=2, rng=random.Random(3))
    assert s == {"like": 5, "comment": 2, "follow": 2}

    capped = InstagramBot(dry_run=True, limiter=RateLimiter({"like": 2}, path=tmp()), sleep=lambda s: None)
    s = run_session(capped, "travel", likes=5, comments=0, follows=0)
    assert s["like"] == 2                      # cap enforced even though 5 were requested


if __name__ == "__main__":
    for t in (test_rate_limiter, test_delays_and_hours, test_captions, test_dry_run_session_and_limits):
        t()
    print("All tests passed!")
