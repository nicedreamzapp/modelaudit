"""The command line: arguments, exit codes, JSON and terminal output."""

import json
import os
import subprocess
import sys

import pytest

from helpers import git_checkout, make_tree
from modelaudit.__main__ import _wrap, main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGPL = "GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3, 19 November 2007\n"
GPL3 = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n"
MIT = "Permission is hereby granted, free of charge, to any person obtaining a copy"


@pytest.fixture
def stack(tmp_path):
    """A small stack: an AGPL engine, a GPL tool, an MIT lib, and a Llama model."""
    spec = {}
    for name, text in (("engine", AGPL), ("tool", GPL3), ("lib", MIT)):
        spec.update({f"{name}/{k}": v for k, v in git_checkout().items()})
        spec[f"{name}/LICENSE"] = text
    # Distinct names, so the no-remote checkouts are not collapsed into one.
    spec["engine/.git/config"] = '[remote "origin"]\n\turl = https://github.com/o/engine\n'
    spec["tool/.git/config"] = '[remote "origin"]\n\turl = https://github.com/o/tool\n'
    spec["lib/.git/config"] = '[remote "origin"]\n\turl = https://github.com/o/lib\n'
    spec["models/llama/model.safetensors"] = ""
    spec["models/llama/LICENSE"] = "LLAMA 3 COMMUNITY LICENSE AGREEMENT"
    return make_tree(tmp_path, spec)


def run_json(capsys, *args):
    code = main([*args, "--offline", "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_json_service_mode(stack, capsys):
    code, out = run_json(capsys, stack, "--ship", "service")
    assert code == 1
    assert out["ship_mode"] == "service"
    assert out["root"] == stack
    sev = {f["name"]: f["severity"] for f in out["findings"]}
    assert sev == {"o/engine": "blocker", "o/tool": "ok", "o/lib": "attribution",
                   "llama": "review"}


def test_json_findings_sorted_by_severity(stack, capsys):
    _, out = run_json(capsys, stack)
    order = [f["severity"] for f in out["findings"]]
    assert order == ["blocker", "attribution", "review", "ok"]


def test_json_findings_carry_explanations(stack, capsys):
    _, out = run_json(capsys, stack)
    for f in out["findings"]:
        assert {"kind", "path", "name", "license", "source", "severity",
                "headline", "detail"} <= set(f)


def test_app_mode_gpl_becomes_blocker(stack, capsys):
    _, out = run_json(capsys, stack, "--ship", "app")
    sev = {f["name"]: f["severity"] for f in out["findings"]}
    assert sev["o/tool"] == "blocker"


def test_private_mode_has_no_blocker(stack, capsys):
    code, out = run_json(capsys, stack, "--ship", "private")
    assert code == 0
    assert "blocker" not in {f["severity"] for f in out["findings"]}


def test_default_ship_mode_is_service(stack, capsys):
    _, out = run_json(capsys, stack)
    assert out["ship_mode"] == "service"


def test_text_report(stack, capsys):
    code = main([stack, "--offline"])
    out = capsys.readouterr().out
    assert code == 1
    assert "\033[" not in out                     # not a tty, so no colour
    assert "shipping as: service" in out
    assert "4 dependencies found, offline mode" in out
    assert "✗ BLOCKER" in out and "o/engine" in out
    assert "AGPL over a network" in out
    assert "? REVIEW" in out and "llama" in out
    assert "Anything marked REVIEW" in out
    # Clean results are hidden without --all.
    assert "o/lib" not in out and "o/tool" not in out
    assert "1 blocker" in out and "1 attribution" in out and "1 ok" in out


def test_text_report_all_shows_clean_results(stack, capsys):
    main([stack, "--offline", "--all"])
    out = capsys.readouterr().out
    assert "o/lib" in out and "o/tool" in out


def test_text_report_shows_license_source(stack, capsys):
    main([stack, "--offline"])
    assert "↳ license from: " in capsys.readouterr().out


def test_text_report_wraps_detail(stack, capsys):
    main([stack, "--offline", "--all"])
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("  ") and not line.startswith("  ↳"):
            assert len(line) <= 2 + 76


def test_nothing_to_worry_about(tmp_path, capsys):
    make_tree(tmp_path, {**{f"lib/{k}": v for k, v in git_checkout().items()},
                         "lib/LICENSE": MIT})
    code = main([str(tmp_path), "--offline"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Nothing to worry about in this mode." in out
    assert "Run with --all" in out


def test_empty_directory(tmp_path, capsys):
    assert main([str(tmp_path), "--offline"]) == 0
    assert "0 dependencies found" in capsys.readouterr().out


def test_depth_flag(tmp_path, capsys):
    make_tree(tmp_path, {"a/b/c/model.gguf": ""})
    _, out = run_json(capsys, str(tmp_path), "--depth", "2")
    assert out["findings"] == []
    _, out = run_json(capsys, str(tmp_path), "--depth", "6")
    assert len(out["findings"]) == 1


def test_not_a_directory(tmp_path, capsys):
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(SystemExit) as e:
        main([str(f)])
    assert e.value.code == 2
    assert "not a directory" in capsys.readouterr().err


def test_bad_ship_mode(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        main([str(tmp_path), "--ship", "saas"])
    assert e.value.code == 2


def test_python_dash_m_entry_point(stack):
    # The real `python -m modelaudit` path, including the process exit code.
    p = subprocess.run([sys.executable, "-m", "modelaudit", stack, "--offline", "--json"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert p.returncode == 1
    assert json.loads(p.stdout)["ship_mode"] == "service"


# ------------------------------------------------------------------ _wrap

def test_wrap_respects_width():
    text = "the quick brown fox jumps over the lazy dog " * 10
    lines = _wrap(text, 20)
    assert all(len(l) <= 20 for l in lines)
    assert " ".join(lines) == " ".join(text.split())


def test_wrap_empty():
    assert _wrap("", 76) == []
    assert _wrap("   ", 76) == []


def test_wrap_short_text_is_one_line():
    assert _wrap("hello  world", 76) == ["hello world"]
