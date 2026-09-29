from pathlib import Path
from unittest.mock import Mock
import pytest
import requests
from ur3_llm_control.llm_planner import LLMPlanner, PlannerError
from ur3_llm_control.task_validator import PlanValidator, ValidationError

PROMPT=Path(__file__).resolve().parents[1]/"prompt/planner_prompt.txt"
ENV={"NINEROUTER_BASE_URL":"http://localhost:20128/v1","NINEROUTER_API_KEY":"test-only","NINEROUTER_MODEL":"test"}
def planner(data):
    session=Mock(); session.post.return_value.json.return_value=data
    return LLMPlanner(PROMPT,ENV,session),session

def test_success_nonstreaming():
    p,s=planner({"choices":[{"message":{"content":'{"plan":[{"skill":"home"}]}'}}]})
    assert p.plan("Về nhà")["plan"] == [{"skill":"home"}]
    assert s.post.call_args.kwargs["json"]["stream"] is False
    assert s.post.call_args.kwargs["json"]["max_tokens"] == 256
    assert s.post.call_args.kwargs["json"]["tool_choice"]["function"]["name"] == "emit_plan"

def test_valid_plan_is_returned_unchanged():
    raw={"plan":[{"skill":"pick","object":"red_cube"},
                 {"skill":"place","object":"red_cube","zone":"zone_b"},
                 {"skill":"home"}]}
    p,_=planner({"choices":[{"message":{"tool_calls":[{"function":{"arguments":__import__("json").dumps(raw)}}]}}]})
    assert p.plan("move it") == raw

def test_missing_place_object_is_not_inferred():
    raw={"plan":[{"skill":"pick","object":"red_cube"},
                 {"skill":"place","zone":"zone_b"}, {"skill":"home"}]}
    p,_=planner({"choices":[{"message":{"tool_calls":[{"function":{"arguments":__import__("json").dumps(raw)}}]}}]})
    result=p.plan("move red to B")
    assert result == raw
    with pytest.raises(ValidationError,match="missing required field.*object"):
        PlanValidator().validate(result)

def test_missing_final_home_is_not_appended():
    raw={"plan":[{"skill":"pick","object":"red_cube"},
                 {"skill":"place","object":"red_cube","zone":"zone_b"}]}
    p,_=planner({"choices":[{"message":{"tool_calls":[{"function":{"arguments":__import__("json").dumps(raw)}}]}}]})
    result=p.plan("move red to B")
    assert result == raw
    with pytest.raises(ValidationError,match="end with exactly home"):
        PlanValidator().validate(result)

def test_revise_plan_resends_trusted_context_and_validator_error():
    session=Mock()
    session.post.return_value.json.return_value={"choices":[{"message":{"tool_calls":[
        {"function":{"arguments":' {"plan":[{"skill":"home"}] } '}}
    ]}}]}
    p=LLMPlanner(PROMPT,ENV,session)
    rejected={"plan":[{"skill":"pick","object":"red_cube"}]}
    context={"object_locations":{"red_cube":"source"}}
    result=p.revise_plan("Move red to B",context,rejected,"plan must end with exactly home()")
    assert result == {"plan":[{"skill":"home"}]}
    messages=session.post.call_args.kwargs["json"]["messages"]
    assert messages[1]["content"].startswith("Trusted context:")
    assert messages[2]["content"] == "Move red to B"
    assert __import__("json").loads(messages[3]["content"]) == rejected
    assert "plan must end with exactly home()" in messages[4]["content"]

def test_empty_llm_plan_is_preserved_then_validator_rejects():
    p,s=planner({"choices":[{"message":{"tool_calls":[{"function":{"arguments":'{"plan":[]}'}}]}}]})
    result=p.plan("impossible request")
    assert result == {"plan":[]}
    assert s.post.call_args.kwargs["json"]["tools"][0]["function"]["parameters"]["properties"]["plan"]["minItems"] == 0
    with pytest.raises(ValidationError,match="empty.*no executable action"):
        PlanValidator().validate(result)

def test_malformed_explicit_request_fails_without_rule_fallback():
    p,_=planner({"choices":[{"message":{"content":"I will move the red cube to zone B."}}]})
    with pytest.raises(PlannerError,match="malformed JSON"):
        p.plan("Put the red cube in zone B")
    assert not hasattr(p,"_fallback_explicit_move")
    assert not hasattr(p,"_normalise_plan")

def test_missing_env():
    with pytest.raises(PlannerError,match="Missing environment"): LLMPlanner(PROMPT,{})

@pytest.mark.parametrize("data,match",[(None,"choices"),({},"choices"),({"choices":[]},"choices"),
 ({"choices":[{}]},"message"),({"choices":[{"message":{}}]},"content"),
 ({"choices":[{"message":{"content":"```json {} ```"}}]},"malformed"),
 ({"choices":[{"message":{"content":'{"plan":[],"plan":[]}'}}]},"malformed"),
 ({"choices":[{"message":{"content":'{"plan":NaN}'}}]},"malformed")])
def test_bad_responses(data,match):
    p,_=planner(data)
    with pytest.raises(PlannerError,match=match): p.plan("test")

@pytest.mark.parametrize("error,match",[(requests.Timeout(),"timeout"),(requests.ConnectionError(),"connect")])
def test_network(error,match):
    p,s=planner({}); s.post.side_effect=error
    with pytest.raises(PlannerError,match=match): p.plan("test")

def test_http():
    p,s=planner({}); response=Mock(status_code=401)
    s.post.return_value.raise_for_status.side_effect=requests.HTTPError(response=response)
    with pytest.raises(PlannerError,match="401"): p.plan("test")


def test_student_intent_classifier_is_separate_and_does_not_plan():
    session=Mock()
    response=Mock()
    response.json.return_value={"choices":[{"message":{"content":'{"student_specific":true}'}}]}
    session.post.return_value=response
    p=LLMPlanner(PROMPT,ENV,session)
    assert p.classify_student_task("Arrange all objects according to my student ID.") is True
    request=session.post.call_args.kwargs["json"]
    assert "Do not create a robot plan" in request["messages"][0]["content"]
    assert "skill" not in request["messages"][0]["content"].lower()
    assert request["messages"][-1]["content"] == "Arrange all objects according to my student ID."
    assert request["max_tokens"] == 32

def test_student_intent_classifier_accepts_false_for_regular_request():
    session=Mock()
    response=Mock()
    response.json.return_value={"choices":[{"message":{"content":'{"student_specific":false}'}}]}
    session.post.return_value=response
    p=LLMPlanner(PROMPT,ENV,session)
    assert p.classify_student_task("Put the red cube in zone B.") is False

@pytest.mark.parametrize("content", ['{"student_specific":"yes"}', '{"student_specific":true,"extra":false}', '{"student_specific":1}'])
def test_bad_intent_response(content):
    p,s=planner({"choices":[{"message":{"content":content}}]})
    with pytest.raises(PlannerError,match="exactly a boolean"):
        p.classify_student_task("Arrange everything for my student ID")
