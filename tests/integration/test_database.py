from types import SimpleNamespace

from database import get_session, init_db
from database.queries import (
    attach_referral_to_user,
    count_registered_referrals,
    ensure_referral_code,
    get_or_create_user,
    get_user_by_pubg_player_id,
    get_user_by_telegram_id,
    grant_registration_and_referral_rewards,
    update_user_registration,
)


def test_database_user_crud_and_pubg_binding():
    init_db()
    tg_user = SimpleNamespace(id=987654321, username="tester", first_name="Test", last_name="User")
    with get_session() as session:
        user = get_or_create_user(session, tg_user)
        assert user.telegram_id == 987654321
        update_user_registration(
            session,
            telegram_id=987654321,
            pubg_player_id="account.test-binding",
            pubg_name="BindingTester",
            pubg_rank="Diamond 2",
            pubg_kd="2.50",
            pubg_shard="steam",
            age=20,
            hours_per_week=12,
            pubg_level=55,
            pubg_total_matches=120,
            pubg_total_wins=18,
            pubg_total_kills=340,
            pubg_total_damage=15000.0,
            pubg_headshot_kills=45,
            pubg_avg_damage=125.0,
            pubg_win_rate=15.0,
            pubg_top10s=60,
            pubg_stats_json='{"ok": true}',
        )

    with get_session() as session:
        fetched = get_user_by_telegram_id(session, 987654321)
        assert fetched is not None
        assert fetched.username == "tester"
        assert fetched.pubg_player_id == "account.test-binding"
        assert fetched.pubg_name == "BindingTester"
        assert fetched.pubg_total_matches == 120
        assert fetched.pubg_level == 55
        assert get_user_by_pubg_player_id(session, "account.test-binding") is not None



def test_referral_reward_flow():
    init_db()
    inviter_tg = SimpleNamespace(id=111111111, username="inviter", first_name="Inv", last_name="Iter")
    invited_tg = SimpleNamespace(id=222222222, username="invited", first_name="New", last_name="Player")

    with get_session() as session:
        inviter = get_or_create_user(session, inviter_tg)
        code = ensure_referral_code(session, inviter)
        invited = get_or_create_user(session, invited_tg)
        ok, _ = attach_referral_to_user(session, invited, code)
        assert ok is True
        update_user_registration(
            session,
            telegram_id=222222222,
            pubg_player_id="account.referral-test",
            pubg_name="ReferralTester",
            pubg_rank="Gold 1",
            pubg_kd="1.80",
            pubg_shard="steam",
            age=18,
            hours_per_week=8,
        )
        invited = get_user_by_telegram_id(session, 222222222)
        grant_registration_and_referral_rewards(session, invited)

    with get_session() as session:
        inviter = get_user_by_telegram_id(session, 111111111)
        invited = get_user_by_telegram_id(session, 222222222)
        assert inviter.points >= 30
        assert invited.points >= 25
        assert count_registered_referrals(session, inviter.id) >= 1
        assert invited.referral_points_paid is True
