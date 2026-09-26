from pathlib import Path
from unittest.mock import Mock
import pytest
import requests
from ur3_llm_control.llm_planner import LLMPlanner, PlannerError

PROMPT=Path(__file__).resolve().parents[1]/"prompt/planner_prompt.txt"
ENV={"NINEROUTER_BASE_URL":"http://localhost:20128/v1","NINEROUTER_API_KEY":"test-only","NINEROUTER_MODEL":"test"}
def planner(data):
    session=Mock(); session.post.return_value.json.return_value=data
    return LLMPlanner(PROMPT,ENV,session),session

def test_success_nonstreaming():
    p,s=planner({"choices":[{"message":{"content":'{"plan":[{"skill":"home"}]}'}}]})
    assert p.plan("Về nhà")["plan"] == [{"skill":"home"}]
    assert s.post.call_args.kwargs["json"]["stream"] is False

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
