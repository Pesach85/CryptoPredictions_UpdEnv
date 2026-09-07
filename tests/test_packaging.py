"""Packaging / path resolution smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from cryptopredictions.paths import (
    AppConfig,
    discover_repo_root,
    ensure_sys_path,
    platform_name,
)


def test_discover_repo_root_from_package():
    root = discover_repo_root()
    assert (root / "services").is_dir()
    assert (root / "api" / "main.py").is_file()


def test_ensure_sys_path_idempotent():
    root = ensure_sys_path()
    again = ensure_sys_path(root)
    assert root == again


def test_app_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    from cryptopredictions import paths as paths_mod

    cfg = AppConfig(mode="dev-linked", repo_root=str(discover_repo_root()), api_port=8010)
    saved = paths_mod.save_config(cfg)
    assert saved.exists()
    loaded = paths_mod.load_config()
    assert loaded.api_port == 8010
    assert loaded.mode == "dev-linked"


def test_platform_name_known():
    assert platform_name() in {"windows", "linux", "macos"} or platform_name()


def test_icon_generator(tmp_path):
    from scripts.generate_icons import write_png

    # import via path
    import importlib.util

    root = discover_repo_root()
    spec = importlib.util.spec_from_file_location(
        "generate_icons", root / "scripts" / "generate_icons.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    out = tmp_path / "icon.png"
    mod.write_png(out, 64)
    assert out.stat().st_size > 100
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_elite_quality_gate_script_levels():
    """Gate script is the Verify entry point for agent-orchestration / elite-quality-gate."""
    root = discover_repo_root()
    path = root / "scripts" / "run_elite_quality_gate.py"
    assert path.is_file()
    env = {**os.environ, "PYTHONPATH": str(root)}
    unit = subprocess.run(
        [sys.executable, str(path), "--level", "unit", "--list-steps"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    ci = subprocess.run(
        [sys.executable, str(path), "--level", "ci", "--list-steps"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    unit_steps = set(json.loads(unit.stdout)["steps"])
    ci_steps = set(json.loads(ci.stdout)["steps"])
    assert unit_steps == {"unit_core", "unit_packaging"}
    assert "cli_projection" in ci_steps
    assert "refresh_status" in ci_steps
    assert unit_steps.issubset(ci_steps)
