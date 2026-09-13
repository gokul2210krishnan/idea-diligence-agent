from pathlib import Path

from src.main import build_parser, main


def test_parser_flags():
    args = build_parser().parse_args(["--demo", "--json", "-o", "out.json", "ignored idea"])
    assert args.demo is True
    assert args.json is True
    assert args.output == Path("out.json")


def test_demo_cli_json(capsys):
    assert main(["--demo", "--json"]) == 0
    captured = capsys.readouterr().out
    assert "decision" in captured
    assert "independent restaurants" in captured.lower()


def test_demo_cli_writes_markdown(tmp_path: Path):
    target = tmp_path / "report.md"
    assert main(["--demo", "-o", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    assert "# Idea Diligence Report" in text
