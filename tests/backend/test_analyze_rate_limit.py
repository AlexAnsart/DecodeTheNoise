from backend.analyze.rate_limit import RateLimiter


def test_rate_limit_window_slides() -> None:
    now = [0.0]
    limiter = RateLimiter(limit=2, window=60.0, clock=lambda: now[0])

    assert [limiter.allow("a"), limiter.allow("a"), limiter.allow("a")] == [True, True, False]
    assert limiter.allow("b")
    now[0] = 59.9
    assert not limiter.allow("a")
    now[0] = 60.0
    assert limiter.allow("a")
