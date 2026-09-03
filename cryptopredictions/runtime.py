"""Process supervision: FastAPI (uvicorn) and optional Streamlit."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptopredictions.paths import AppConfig, discover_repo_root, ensure_sys_path


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen | None = None
    url: str | None = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self, timeout: float = 5.0) -> None:
        if not self.process:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


@dataclass
class RuntimeHub:
    config: AppConfig
    repo_root: Path
    api: ManagedProcess = field(default_factory=lambda: ManagedProcess("api"))
    streamlit: ManagedProcess = field(default_factory=lambda: ManagedProcess("streamlit"))
    log_dir: Path | None = None

    def __post_init__(self) -> None:
        ensure_sys_path(self.repo_root)
        if self.log_dir is None:
            from cryptopredictions.paths import cache_dir

            self.log_dir = cache_dir() / "logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config(cls, config: AppConfig | None = None) -> "RuntimeHub":
        from cryptopredictions.paths import load_config

        cfg = config or load_config()
        root = discover_repo_root(cfg.repo_root)
        return cls(config=cfg, repo_root=root)

    def _python(self) -> str:
        return self.config.python_executable or sys.executable

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CRYPTOPREDICTIONS_ROOT"] = str(self.repo_root)
        env["PYTHONPATH"] = str(self.repo_root)
        return env

    @staticmethod
    def port_open(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4)
            return sock.connect_ex((host, port)) == 0

    def start_api(self) -> ManagedProcess:
        host = self.config.api_host
        port = self.config.api_port
        if self.port_open(host, port):
            self.api.url = f"http://{host}:{port}"
            return self.api
        log_path = self.log_dir / "api.log"  # type: ignore[operator]
        log_fp = open(log_path, "a", encoding="utf-8")
        cmd = [
            self._python(),
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        self.api.process = subprocess.Popen(
            cmd,
            cwd=str(self.repo_root),
            env=self._env(),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
        )
        self.api.url = f"http://{host}:{port}"
        for _ in range(40):
            if self.port_open(host, port):
                break
            time.sleep(0.25)
        return self.api

    def start_streamlit(self) -> ManagedProcess:
        port = self.config.streamlit_port
        host = "127.0.0.1"
        if self.port_open(host, port):
            self.streamlit.url = f"http://{host}:{port}"
            return self.streamlit
        log_path = self.log_dir / "streamlit.log"  # type: ignore[operator]
        log_fp = open(log_path, "a", encoding="utf-8")
        cmd = [
            self._python(),
            "-m",
            "streamlit",
            "run",
            str(self.repo_root / "app_projection.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ]
        self.streamlit.process = subprocess.Popen(
            cmd,
            cwd=str(self.repo_root),
            env=self._env(),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
        )
        self.streamlit.url = f"http://{host}:{port}"
        for _ in range(60):
            if self.port_open(host, port):
                break
            time.sleep(0.25)
        return self.streamlit

    def stop_all(self) -> None:
        self.streamlit.stop()
        self.api.stop()

    def status(self) -> dict[str, Any]:
        return {
            "repo_root": str(self.repo_root),
            "mode": self.config.mode,
            "api": {"running": self.api.running or self.port_open(self.config.api_host, self.config.api_port), "url": self.api.url},
            "streamlit": {
                "running": self.streamlit.running
                or self.port_open("127.0.0.1", self.config.streamlit_port),
                "url": self.streamlit.url,
            },
        }
