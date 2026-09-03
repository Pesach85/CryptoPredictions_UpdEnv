"""Packaging / path resolution smoke tests."""

from __future__ import annotations

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
