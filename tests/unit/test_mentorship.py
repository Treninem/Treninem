from features.mentorship.mentor_validator import can_be_mentor, mentor_can_teach_student


def test_can_be_mentor():
    assert can_be_mentor("Crown I")
    assert can_be_mentor("Master")
    assert not can_be_mentor("Gold IV")


def test_mentor_can_teach_student():
    assert mentor_can_teach_student("Crown I", "Gold II")
    assert not mentor_can_teach_student("Gold II", "Crown I")
    assert not mentor_can_teach_student("Diamond", "Diamond")
