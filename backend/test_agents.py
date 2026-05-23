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

def test_strip_fences_with_prose():
    from agents import _strip_fences
    llm_output = "Here is the code:\n```python\ndef foo():\n    return 42\n```\nNote: this is correct."
    extracted = _strip_fences(llm_output)
    assert extracted == "def foo():\n    return 42"


# ---------- memory_store tests ----------

def _isolated_history(tmp_path, monkeypatch):
    """Point memory_store at a tmp file so tests don't pollute real memory/."""
    import memory_store
    tmp_history = tmp_path / "audit_history.jsonl"
    monkeypatch.setattr(memory_store, "HISTORY_PATH", str(tmp_history))
    return memory_store, tmp_history


def test_memory_recall_empty(tmp_path, monkeypatch):
    memory_store, _ = _isolated_history(tmp_path, monkeypatch)
    assert memory_store.recall_history("app/views.py") == []


def test_memory_append_then_recall(tmp_path, monkeypatch):
    memory_store, _ = _isolated_history(tmp_path, monkeypatch)
    memory_store.append_outcome(
        file_path="app/views.py",
        outcome="Heal-Failed",
        summary="Architect output failed AST parse",
        findings=[{"severity": "high", "category": "security", "evidence": "x", "rationale": "y"}],
        simulation={"passed": False, "error": "SyntaxError: unexpected token"},
    )
    memory_store.append_outcome(
        file_path="other/path.py",  # different file — should be filtered out
        outcome="Clean",
        summary="ok",
        findings=[],
        simulation={"skipped": True},
    )
    history = memory_store.recall_history("app/views.py")
    assert len(history) == 1
    assert history[0]["outcome"] == "Heal-Failed"
    assert history[0]["finding_categories"] == ["security"]
    assert history[0]["simulation_error"].startswith("SyntaxError")


def test_memory_recall_respects_limit(tmp_path, monkeypatch):
    memory_store, _ = _isolated_history(tmp_path, monkeypatch)
    for i in range(8):
        memory_store.append_outcome(
            file_path="app/x.py",
            outcome="Clean",
            summary=f"run {i}",
            findings=[],
            simulation={"skipped": True},
        )
    history = memory_store.recall_history("app/x.py", limit=3)
    assert len(history) == 3
    assert history[-1]["summary"] == "run 7"  # newest


def test_memory_recall_tolerates_corrupt_lines(tmp_path, monkeypatch):
    memory_store, tmp_history = _isolated_history(tmp_path, monkeypatch)
    memory_store.append_outcome(
        file_path="app/x.py",
        outcome="Clean",
        summary="good",
        findings=[],
        simulation={"skipped": True},
    )
    # Inject a corrupt line manually
    with open(tmp_history, "a") as f:
        f.write("not valid json at all\n")
    memory_store.append_outcome(
        file_path="app/x.py",
        outcome="Self-Healed",
        summary="after garbage",
        findings=[],
        simulation={"passed": True},
    )
    history = memory_store.recall_history("app/x.py")
    assert len(history) == 2  # corrupt line skipped
    assert history[-1]["outcome"] == "Self-Healed"


def test_format_history_for_prompt():
    from memory_store import format_history_for_prompt
    rendered = format_history_for_prompt([
        {"ts": "2026-05-22T12:00:00Z", "outcome": "Heal-Failed",
         "finding_categories": ["security", "drift"],
         "simulation_error": "SyntaxError"},
    ])
    assert "Heal-Failed" in rendered
    assert "security" in rendered
    assert "SyntaxError" in rendered

    assert format_history_for_prompt([]) == ""
