"""The verifiable reward: velocity, normalization, weights, Goodhart guards."""
import pytest
from conftest import make_row


def test_velocity_older_measurement_scores_lower(sc):
    fresh = make_row("a", views=100, bucket="t1h")
    stale = make_row("b", views=100, bucket="t_night")
    assert sc.rescore(fresh) > sc.rescore(stale)


def test_velocity_same_views_different_ages(sc):
    h1 = sc.rescore(make_row("a", views=240, bucket="t1h"))
    h24 = sc.rescore(make_row("b", views=240, bucket="t_night"))
    assert h1 > h24 * 1.2  # same views at 1/24th the age is clearly faster


def test_follower_normalization_bigger_account_needs_more_views(sc):
    small = sc.rescore(make_row("a", views=100, followers=100))
    big = sc.rescore(make_row("b", views=100, followers=10_000))
    assert small > big


def test_zero_followers_does_not_crash(sc):
    assert sc.rescore(make_row("a", views=10, followers=0)) >= 0


def test_missing_followers_is_age_only(sc):
    # rows without author_followers still score (age normalization only)
    assert sc.rescore(make_row("a", views=10)) >= 0


def test_bookmarks_weight_above_replies_above_likes(sc):
    bk = sc.rescore(make_row("a", views=0, bookmarks=1))
    rp = sc.rescore(make_row("b", views=0, replies=1))
    lk = sc.rescore(make_row("c", views=0, likes=1))
    assert bk > rp > lk


def test_engagement_adds_to_views(sc):
    base = sc.rescore(make_row("a", views=100))
    plus = sc.rescore(make_row("b", views=100, bookmarks=5))
    assert plus > base


def test_reply_bonus_strong_ratio(sc):
    s20 = sc.rescore(make_row("a", rtype="reply", ratio=25))
    s_plain = sc.rescore(make_row("b", rtype="reply", ratio=11))
    assert s20 > s_plain


def test_reply_bonus_default_policy_boundaries(sc):
    at20 = sc.rescore(make_row("a", rtype="reply", ratio=20))
    at19 = sc.rescore(make_row("b", rtype="reply", ratio=19.9))
    assert at20 > at19
    below5 = sc.rescore(make_row("c", rtype="reply", ratio=4))
    at5 = sc.rescore(make_row("d", rtype="reply", ratio=5))
    assert below5 < at5  # low-ratio penalty


def test_original_gets_no_reply_bonus(sc):
    reply = sc.rescore(make_row("a", rtype="reply", ratio=50))
    original = sc.rescore(make_row("b", rtype="original"))
    assert reply > original


def test_author_reply_bonus(sc):
    plain = make_row("b")
    replied = make_row("c")
    replied["features"]["author_replied"] = True
    assert sc.rescore(replied) > sc.rescore(plain)


def test_dead_diary_penalty(sc):
    live = make_row("a", ratio=0.2)
    dead = make_row("b", ratio=0.2)
    dead["features"]["viral_signal"] = "weak_dead_diary"
    assert sc.rescore(dead) < sc.rescore(live) * 0.5


def test_hard_open_small_bonus(sc):
    a = make_row("a")
    b = make_row("b")
    b["features"]["hard_open"] = True
    assert sc.rescore(b) > sc.rescore(a)


def test_off_niche_penalty_from_policy(sc):
    policy = dict(sc.DEFAULT_POLICY, niche_topics=["ads", "checkout"])
    on = make_row("a", topic="ads")
    off = make_row("b", topic="celebrity_gossip")
    assert sc.rescore(off, policy) < sc.rescore(on, policy)


def test_no_niche_list_means_no_penalty(sc):
    off = make_row("a", topic="celebrity_gossip")
    assert sc.rescore(dict(off), dict(sc.DEFAULT_POLICY)) == sc.rescore(dict(off), None)


def test_risky_parent_penalty(sc):
    risky = make_row("a", rtype="reply")
    risky["features"]["parent_risky"] = True
    plain = make_row("b", rtype="reply")
    assert sc.rescore(risky) < sc.rescore(plain)


def test_duplicate_halves_score(sc):
    a = make_row("a")
    plain = sc.rescore(dict(a))
    duped = sc.rescore(dict(a), duplicate=True)
    assert duped == pytest.approx(plain / 2, abs=1e-3)


def test_duplicate_ids_marks_later_row(sc):
    r1 = make_row("first", text="most stores stare at sessions and miss the checkout drop")
    r2 = make_row("second", text="most stores stare at sessions and miss the checkout drop")
    r2["ts"] = "2026-08-21T10:12:00Z"
    r3 = make_row("other", text="completely different words about bid caps and learning phase")
    assert sc.duplicate_ids([r1, r2, r3]) == {"second"}


def test_duplicate_ids_same_text_different_type_not_flagged(sc):
    r1 = make_row("a", rtype="reply", text="same words here")
    r2 = make_row("b", rtype="original", text="same words here")
    assert sc.duplicate_ids([r1, r2]) == set()


def test_policy_parse_defaults_when_no_block(sc):
    assert sc.parse_policy("just prose", "x.md") == sc.DEFAULT_POLICY


def test_policy_parse_overrides(sc):
    text = 'prose\n<!-- skillopt-policy {"reply_bonus_ratio": 15, "niche_topics": ["Ads"]} -->\n'
    p = sc.parse_policy(text, "x.md")
    assert p["reply_bonus_ratio"] == 15.0
    assert p["niche_topics"] == ["Ads"]


def test_policy_parse_rejects_unknown_key(sc):
    with pytest.raises(sc.DataError, match="unknown skillopt-policy key"):
        sc.parse_policy('<!-- skillopt-policy {"bonus": 1} -->', "x.md")


def test_policy_parse_rejects_bad_json(sc):
    with pytest.raises(sc.DataError, match="not valid JSON"):
        sc.parse_policy("<!-- skillopt-policy {nope} -->", "x.md")


def test_policy_parse_rejects_wrong_types(sc):
    with pytest.raises(sc.DataError, match="niche_topics"):
        sc.parse_policy('<!-- skillopt-policy {"niche_topics": "ads"} -->', "x.md")


def test_bootstrap_ci_of_constant_deltas_is_degenerate_at_that_value(sc):
    lo, hi = sc.bootstrap_ci([2.0] * 20, resamples=500, seed=1)
    assert lo == 2.0 and hi == 2.0


def test_bootstrap_ci_excludes_zero_for_clear_effect(sc):
    deltas = [5.0] * 4 + [0.0] * 4
    lo, _hi = sc.bootstrap_ci(deltas, seed=sc.seed_for([f"r{i}" for i in range(8)]))
    assert lo > 0


def test_seed_is_deterministic(sc):
    assert sc.seed_for(["b", "a"]) == sc.seed_for(["a", "b"])
