from features.points_system.rank_updater import get_rank_for_points


def test_get_rank_for_points():
    assert get_rank_for_points(0) == "Новичок"
    assert get_rank_for_points(150) == "Стрелок"
    assert get_rank_for_points(450) == "Тактик"
    assert get_rank_for_points(800) == "Ветеран"
    assert get_rank_for_points(1200) == "Легенда"
