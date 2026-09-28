import pytest
from ur3_llm_control.request_policy import classify_student_request


class FakePlanner:
    def __init__(self, answer):
        self.answer=answer
        self.calls=[]

    def classify_student_task(self, command):
        self.calls.append(command)
        return self.answer


def test_missing_student_config_fails_closed_after_llm_classification():
    planner=FakePlanner(True)
    with pytest.raises(ValueError,match="valid student configuration"):
        classify_student_request(planner,"Arrange for my student ID",False,None,"invalid student config")
    assert planner.calls == ["Arrange for my student ID"]


def test_missing_student_config_allows_classified_ordinary_request():
    planner=FakePlanner(False)
    assert classify_student_request(planner,"Move red to B",False,None,"invalid student config") is False
    assert planner.calls == ["Move red to B"]


def test_strict_student_mode_requires_mapping_without_classifier_call():
    planner=FakePlanner(False)
    with pytest.raises(ValueError,match="valid student configuration"):
        classify_student_request(planner,"Arrange",True,None)
    assert planner.calls == []
