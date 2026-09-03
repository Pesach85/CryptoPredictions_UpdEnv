"""CLI entry points for CryptoPredictions desktop / services."""

from __future__ import annotations

import argparse
import json
import sys


def cmd_desktop(_: argparse.Namespace) -> int:
    from cryptopredictions.desktop_shell import run_desktop

    return run_desktop()


def cmd_api(args: argparse.Namespace) -> int:
    from cryptopredictions.paths import load_config
    from cryptopredictions.runtime import RuntimeHub

    hub = RuntimeHub.from_config(load_config())
    hub.config.api_host = args.host
    hub.config.api_port = args.port
    proc = hub.start_api()
    print(json.dumps({"url": proc.url, "pid": proc.process.pid if proc.process else None}, indent=2))
    if args.foreground and proc.process:
        return proc.process.wait()
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    from cryptopredictions.paths import load_config
    from cryptopredictions.runtime import RuntimeHub

    print(json.dumps(RuntimeHub.from_config(load_config()).status(), indent=2))
    return 0


def cmd_config_show(_: argparse.Namespace) -> int:
    from cryptopredictions.paths import config_path, load_config

    cfg = load_config()
    print(json.dumps({"path": str(config_path()), "config": cfg.to_dict()}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cryptopredictions", description="CryptoPredictions launcher")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("desktop", help="Native Qt desktop shell")
    d.set_defaults(func=cmd_desktop)

    a = sub.add_parser("api", help="Start FastAPI (uvicorn) from live repo")
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=8000)
    a.add_argument("--foreground", action="store_true")
    a.set_defaults(func=cmd_api)

    s = sub.add_parser("status", help="Show service status")
    s.set_defaults(func=cmd_status)

    c = sub.add_parser("config", help="Show config path and contents")
    c.set_defaults(func=cmd_config_show)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
