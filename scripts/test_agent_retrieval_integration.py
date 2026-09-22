"""Run offline agent integration checks without changing production indexes."""
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    return subprocess.call(
        [sys.executable, "-m", "pytest", "-q", "tests/test_agent.py"], cwd=root
    )


if __name__ == "__main__":
    raise SystemExit(main())
