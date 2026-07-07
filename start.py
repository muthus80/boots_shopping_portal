#!/usr/bin/env python3
"""Cross-platform dev server launcher — works on Windows and EC2/Linux.

Usage:
    python start.py                   # default ports
    BE_PORT=8001 FE_PORT=3001 python start.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BE_PORT = int(os.getenv("BE_PORT", "8000"))
FE_PORT = int(os.getenv("FE_PORT", "3000"))

be = subprocess.Popen(
    [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--reload", f"--port={BE_PORT}", "--host", "0.0.0.0",
    ],
    cwd=ROOT,
)
print(f"Backend:  http://localhost:{BE_PORT}/docs")

fe = subprocess.Popen(
    ['npm', 'run', 'dev', '--', '--port', str(FE_PORT)],
    cwd=ROOT / 'frontend',
    shell=(sys.platform == 'win32'),
)
print(f'Frontend: http://localhost:{FE_PORT}')

print("Ctrl+C to stop.")
try:
    be.wait()
except KeyboardInterrupt:
    be.terminate()
    fe.terminate()

