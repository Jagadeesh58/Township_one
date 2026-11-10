"""Start the FastAPI and Vite development servers and stop both on exit."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    processes: list[subprocess.Popen] = []
    commands = [
        ([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"], ROOT),
        ([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], ROOT / "frontend"),
    ]
    try:
        for command, cwd in commands:
            processes.append(subprocess.Popen(command, cwd=cwd))
        print("Backend:  http://127.0.0.1:8000/docs", flush=True)
        print("Frontend: http://127.0.0.1:5173", flush=True)
        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
