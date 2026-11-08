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


def test_targeting_features_are_not_rewarded(sc):
    # Parent ratio is a targeting choice, not an outcome: same counters, same reward.
    gold = sc.rescore(make_row("a", rtype="reply", ratio=25))
    weak = sc.rescore(make_row("b", rtype="reply", ratio=2))
    original = sc.rescore(make_row("c", rtype="original"))
    assert gold == weak == original


def test_author_reply_bonus(sc):
    plain = make_row("b")
    replied = make_row("c")
    replied["features"]["author_replied"] = True
    assert sc.rescore(replied) > sc.rescore(plain)


def test_dead_diary_and_hard_open_do_not_change_the_reward(sc):
    plain = make_row("a", ratio=0.2)
    dead = make_row("b", ratio=0.2)
    dead["features"]["viral_signal"] = "weak_dead_diary"
    opened = make_row("c")
    opened["features"]["hard_open"] = True
    assert sc.rescore(dead) == sc.rescore(plain) == sc.rescore(opened)


def test_config_follower_default_applies_to_rows_without_followers(sc):
    no_feat = make_row("a", views=100)
    logged = make_row("b", views=100, followers=500)
    assert sc.rescore(no_feat, {"author_followers": 500}) == sc.rescore(logged)


def test_off_niche_penalty_from_policy(sc):
    policy = {"niche_topics": ["ads", "checkout"]}
    on = make_row("a", topic="ads")
    off = make_row("b", topic="celebrity_gossip")
    assert sc.rescore(off, policy) < sc.rescore(on, policy)


def test_no_niche_list_means_no_penalty(sc):
    off = make_row("a", topic="celebrity_gossip")
    assert sc.rescore(dict(off), {}) == sc.rescore(dict(off), None)


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
    text = 'prose\n<!-- skillopt-policy {"min_parent_ratio": 15, "topics": [" Ads "]} -->\n'
    p = sc.parse_policy(text, "x.md")
    assert p["min_parent_ratio"] == 15.0
    assert p["topics"] == ["ads"]
    assert p["skip_dead_diary"] is False


def test_policy_parse_rejects_reward_knobs(sc):
    # The old design let a skill rewrite its own reward; those keys are gone.
    for key in ("reply_bonus_ratio", "niche_topics", "dead_diary_multiplier"):
        with pytest.raises(sc.DataError, match="unknown skillopt-policy key"):
            sc.parse_policy(f'<!-- skillopt-policy {{"{key}": 1}} -->', "x.md")


def test_selects_applies_each_targeting_rule(sc):
    gold = make_row("a", rtype="reply", ratio=20, topic="ads")
    weak = make_row("b", rtype="reply", ratio=2, topic="ads")
    dead = make_row("c", rtype="original", topic="ads")
    dead["features"]["viral_signal"] = "weak_dead_diary"
    risky = make_row("d", rtype="reply", ratio=20, topic="ops")
    risky["features"]["parent_risky"] = True
    no_ratio = make_row("e", rtype="reply")
    p = dict(sc.DEFAULT_POLICY)
    assert all(sc.selects(r, p) for r in (gold, weak, dead, risky, no_ratio))
    assert not sc.selects(weak, dict(p, min_parent_ratio=12))
    assert not sc.selects(no_ratio, dict(p, min_parent_ratio=12))
    assert sc.selects(dead, dict(p, min_parent_ratio=12))  # originals have no parent
    assert not sc.selects(dead, dict(p, skip_dead_diary=True))
    assert not sc.selects(risky, dict(p, skip_risky_parents=True))
    assert not sc.selects(risky, dict(p, topics=["ads"]))


def test_policy_parse_rejects_unknown_key(sc):
    with pytest.raises(sc.DataError, match="unknown skillopt-policy key"):
        sc.parse_policy('<!-- skillopt-policy {"bonus": 1} -->', "x.md")


def test_policy_parse_rejects_bad_json(sc):
    with pytest.raises(sc.DataError, match="not valid JSON"):
        sc.parse_policy("<!-- skillopt-policy {nope} -->", "x.md")


def test_policy_parse_rejects_wrong_types(sc):
    with pytest.raises(sc.DataError, match="topics"):
        sc.parse_policy('<!-- skillopt-policy {"topics": "ads"} -->', "x.md")
    with pytest.raises(sc.DataError, match="skip_dead_diary"):
        sc.parse_policy('<!-- skillopt-policy {"skip_dead_diary": 1} -->', "x.md")


def test_replay_ci_is_zero_when_both_policies_take_the_same_rows(sc):
    scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    take = [True] * 6
    assert sc.bootstrap_replay_ci(scores, take, take, resamples=300, seed=1) == (0.0, 0.0)


def test_replay_ci_excludes_zero_for_clear_effect(sc):
    scores = [5.0] * 6 + [0.0] * 6
    take_a = [True] * 12
    take_b = [True] * 6 + [False] * 6
    lo, _hi = sc.bootstrap_replay_ci(scores, take_a, take_b, seed=sc.seed_for(["x"]))
    assert lo > 0


def test_two_sample_ci_of_constant_groups_is_degenerate(sc):
    lo, hi = sc.bootstrap_two_sample_ci([1.0] * 8, [3.0] * 8, resamples=300, seed=1)
    assert lo == hi == 2.0


def test_seed_is_deterministic(sc):
    assert sc.seed_for(["b", "a"]) == sc.seed_for(["a", "b"])
