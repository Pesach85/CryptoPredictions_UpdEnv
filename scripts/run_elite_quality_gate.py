#!/usr/bin/env python
"""Elite quality gate — Verify step for agent-orchestration / elite-quality-gate.

Runs the same smoke suite CI uses (plus optional domain checks) so agents have
one evidence-backed command before claiming "no regressions".

Exit 0 = all selected steps passed; non-zero = first failure (printed).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# (name, argv, levels)
STEPS: tuple[tuple[str, list[str], frozenset[str]], ...] = (
    (
        "unit_core",
        [sys.executable, "-m", "pytest", "-q", "tests/test_core.py", "-k", "not projection_smoke"],
        frozenset({"unit", "ci", "domain", "full"}),
    ),
    (
        "unit_packaging",
        [sys.executable, "-m", "pytest", "-q", "tests/test_packaging.py"],
        frozenset({"unit", "ci", "domain", "full"}),
    ),
    (
        "cli_projection",
        [
            sys.executable,
            "project_forward.py",
            "--asset",
            "ETHUSD",
            "--horizon",
            "7",
            "--as-of",
            "2026-08-15",
            "--no-save",
        ],
        frozenset({"ci", "domain", "full"}),
    ),
    (
        "cli_multi_model_fast",
        [
            sys.executable,
            "scripts/august_multi_model_paths.py",
            "ETHUSD",
            "--start",
            "2026-08-01",
            "--end",
            "2026-08-10",
            "--fast",
            "--no-persist",
        ],
        frozenset({"ci", "domain", "full"}),
    ),
    (
        "cli_volatility",
        [
            sys.executable,
            "scripts/volatility_forecast.py",
            "ETHUSD",
            "--threshold",
            "10",
        ],
        frozenset({"ci", "domain", "full"}),
    ),
    (
        "refresh_status",
        [sys.executable, "scripts/refresh_market_data.py", "--status"],
        frozenset({"ci", "domain", "full"}),
    ),
    (
        "android_assets_end",
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path\n"
                "root=Path('packaging/android/CryptoPredictionsApp/app/src/main/assets/ohlcv')\n"
                "assert root.is_dir(), root\n"
                "ends=[]\n"
                "for p in sorted(root.glob('*.csv')):\n"
                "    lines=p.read_text(encoding='utf-8').strip().splitlines()\n"
                "    assert len(lines)>=2, p\n"
                "    ends.append((p.name, lines[-1].split(',')[0][:10]))\n"
                "print({'assets':len(ends),'ends':ends})\n"
                "assert all(e[1]>='2026-09-07' for e in ends), ends\n"
            ),
        ],
        frozenset({"domain", "full"}),
    ),
)


def _run_step(name: str, argv: list[str]) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        argv,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    return {
        "name": name,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "argv": argv,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CryptoPredictions elite quality gate (Verify step).",
        epilog=(
            "Levels:\n"
            "  unit   — pytest core + packaging only\n"
            "  ci     — mirror GitHub Actions ci-smoke\n"
            "  domain — ci + same domain CLIs (default for agents)\n"
            "  full   — alias of domain (extensible for install checks)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--level",
        choices=("unit", "ci", "domain", "full"),
        default="domain",
        help="Gate depth (default: domain)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON summary",
    )
    parser.add_argument(
        "--list-steps",
        action="store_true",
        help="Print step names for --level and exit 0",
    )
    args = parser.parse_args()

    selected = [(n, a, lv) for (n, a, lv) in STEPS if args.level in lv]

    if args.list_steps:
        payload = {"level": args.level, "steps": [n for (n, _, _) in selected]}
        print(json.dumps(payload, indent=2))
        return 0

    results: list[dict] = []
    failed = False

    for name, argv, _levels in selected:
        result = _run_step(name, argv)
        results.append(result)
        status = "PASS" if result["ok"] else "FAIL"
        print(f"[{status}] {name}")
        if not result["ok"]:
            failed = True
            if result["stderr_tail"].strip():
                print(result["stderr_tail"])
            elif result["stdout_tail"].strip():
                print(result["stdout_tail"])
            break

    summary = {
        "level": args.level,
        "passed": not failed,
        "steps_run": len(results),
        "steps_planned": len(selected),
        "results": results,
        "simulation_only": True,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"elite_quality_gate level={args.level} "
            f"passed={summary['passed']} "
            f"steps={summary['steps_run']}/{summary['steps_planned']}"
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
