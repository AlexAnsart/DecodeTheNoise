import pytest

from pipelines.review.band_estimate import BandCounts, estimate_cascade, read_enough


def band(size: int, kept_yes: int, kept_no: int, left_yes: int, left_no: int) -> BandCounts:
    return BandCounts(0.0, size, kept_yes, kept_no, left_yes, left_no)


def test_one_band_gives_the_plain_shares_of_the_posts_read() -> None:
    measured = estimate_cascade([band(1000, kept_yes=45, kept_no=5, left_yes=15, left_no=35)])

    assert (measured["read"], measured["read_yes"], measured["kept"], measured["kept_yes"]) == (
        100,
        60,
        50,
        45,
    )
    assert measured["after_probe"]["value"] == pytest.approx(0.60)
    assert measured["after_review"]["value"] == pytest.approx(0.90)
    assert measured["true_positives_kept"]["value"] == pytest.approx(0.75)
    for name in ("after_probe", "after_review", "true_positives_kept"):
        rate = measured[name]
        assert rate["low"] < rate["value"] < rate["high"]


def test_a_band_counts_for_the_posts_it_holds_not_for_the_posts_read() -> None:
    # The small band was read as much as the large one, and is nine times smaller.
    top = band(100, kept_yes=40, kept_no=0, left_yes=10, left_no=0)
    low = band(900, kept_yes=10, kept_no=10, left_yes=10, left_no=20)

    measured = estimate_cascade([top, low])

    # Yes posts of the split: 100 + 900 * 0.4 = 460 of 1,000.
    assert measured["after_probe"]["value"] == pytest.approx(0.46)
    # Kept: 80 + 360, of which a yes: 80 + 180.
    assert measured["after_review"]["value"] == pytest.approx(260 / 440)
    assert measured["true_positives_kept"]["value"] == pytest.approx(260 / 460)


def test_more_posts_read_give_a_narrower_interval() -> None:
    few = estimate_cascade([band(1000, 9, 1, 3, 7)])["after_review"]
    many = estimate_cascade([band(1000, 90, 10, 30, 70)])["after_review"]

    assert many["high"] - many["low"] < few["high"] - few["low"]


def test_a_band_that_holds_posts_and_was_not_read_leaves_no_estimate() -> None:
    measured = estimate_cascade([band(100, 10, 0, 0, 0), band(500, 0, 0, 0, 0)])

    assert measured["after_probe"] is None and measured["after_review"] is None
    assert measured["read"] == 10
    # An empty band is no obstacle: it holds no post of the split.
    assert estimate_cascade([band(100, 10, 0, 0, 0), band(0, 0, 0, 0, 0)])["after_review"]


def test_a_probe_is_measured_down_to_the_first_band_hardly_read() -> None:
    head = band(100, 25, 1, 6, 17)
    hardly_read = band(2900, 2, 0, 0, 8)
    below = band(5000, 30, 5, 5, 30)

    # The band under the head has 10 posts read for 2,900 held: it stops the measure, and so
    # does everything under it, however well read.
    assert read_enough([head, hardly_read, below]) == [head]
    assert read_enough([head, below]) == [head, below]
    # An empty band holds no post: it is no gap.
    assert read_enough([head, band(0, 0, 0, 0, 0), below]) == [head, band(0, 0, 0, 0, 0), below]
