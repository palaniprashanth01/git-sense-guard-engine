import pytest
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import simulate, AgentEvent
from agent_runtime import assert_role_allowed

def test_simulate_happy_python():
    events = []
    res = simulate("app/main.py", "def foo():\n    return 42\n", events)
    assert res["passed"] is True
    assert "python-ast: ok" in res["checks"]
    assert "secret-scan: ok" in res["checks"]
    assert any(ev.level == "success" for ev in events)

def test_simulate_sad_python():
    events = []
    res = simulate("app/main.py", "def foo(\n", events)
    assert res["passed"] is False
    assert "python-ast: ok" not in res["checks"]
    assert any(ev.level == "error" for ev in events)

def test_simulate_happy_json():
    events = []
    res = simulate("config.json", '{"name": "test", "active": true}', events)
    assert res["passed"] is True
    assert "json-parse: ok" in res["checks"]

def test_simulate_sad_json():
    events = []
    res = simulate("config.json", '{"name": "test", "active": ', events)
    assert res["passed"] is False
    assert any(ev.level == "error" for ev in events)

def test_simulate_happy_yaml():
    events = []
    res = simulate("config.yaml", 'name: test\nactive: true\n', events)
    assert res["passed"] is True
    assert any("yaml-parse" in c for c in res["checks"])

def test_simulate_sad_yaml():
    events = []
    # Broken YAML structure
    res = simulate("config.yaml", 'name: [test\n- active: true\n', events)
    assert res["passed"] is False
    assert any(ev.level == "error" for ev in events)

def test_simulate_happy_js_ts():
    events = []
    res = simulate("app.ts", "function test() { return (42); }", events)
    assert res["passed"] is True
    assert "brace-balance: ok" in res["checks"]

def test_simulate_sad_js_ts_unbalanced_braces():
    events = []
    res = simulate("app.ts", "function test() { return 42; ", events)
    assert res["passed"] is False
    assert "brace-balance: ok" not in res["checks"]

def test_simulate_sad_js_ts_unbalanced_parens():
    events = []
    res = simulate("app.ts", "function test( { return 42; }", events)
    assert res["passed"] is False
    assert "brace-balance: ok" not in res["checks"]

def test_simulate_secret_leak():
    events = []
    # Leak an OpenAI/Groq-style secret
    res = simulate("app/main.py", "API_KEY = 'sk-test-1234567890abcdefghij'\n", events)
    assert res["passed"] is False
    assert any(ev.level == "error" for ev in events)
    assert "secret-scan: ok" not in res["checks"]

def test_assert_role_allowed_violation_auditor_patch():
    with pytest.raises(PermissionError) as excinfo:
        assert_role_allowed("Auditor", "patch")
    assert "Auditor is not authorized to patch findings" in str(excinfo.value)

def test_assert_role_allowed_happy():
    # Architect is allowed to patch
    assert_role_allowed("Architect", "patch")
    # Auditor is allowed to audit
    assert_role_allowed("Auditor", "audit")
