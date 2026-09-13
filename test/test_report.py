from src.demo_data import load_sample_investigation
from src.report import render_console_report, render_json_report, render_markdown_report


def test_markdown_report_contains_verdict_and_ledger():
    state, scope, budget = load_sample_investigation()
    markdown = render_markdown_report(state, scope, budget)
    assert "# Idea Diligence Report" in markdown
    assert state.verdict.decision.value in markdown
    assert "Evidence ledger" in markdown
    assert "Safety gate: PASSED" in markdown
    assert "3/5" in markdown


def test_json_report_is_parseable():
    import json

    state, scope, budget = load_sample_investigation()
    payload = json.loads(render_json_report(state, scope, budget))
    assert payload["idea"]
    assert payload["verdict"]["decision"] in {"GO", "MODIFY", "KILL"}
    assert payload["scope"]["is_valid"] is True


def test_console_report_includes_decision():
    state, scope, budget = load_sample_investigation()
    text = render_console_report(state, scope, budget)
    assert state.verdict.decision.value in text


def test_console_report_falls_back_when_stdout_is_ascii(monkeypatch):
    class _AsciiStdout:
        encoding = "ascii"

    monkeypatch.setattr("src.report.sys.stdout", _AsciiStdout())
    state, scope, budget = load_sample_investigation()
    text = render_console_report(state, scope, budget)
    assert "# Idea Diligence Report" in text
    assert state.verdict.decision.value in text
