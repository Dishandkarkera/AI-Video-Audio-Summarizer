"""Stable backend launcher (no reload) to keep FastAPI running.
Usage (PowerShell):
  $env:PYTHONPATH = "$PWD\\backend"; python start_backend.py --port 8000

This avoids accidental termination when reusing terminals for other commands.
"""
import argparse, pathlib, sys
import uvicorn

ROOT = pathlib.Path(__file__).parent.resolve()
BACKEND_DIR = ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='127.0.0.1')
parser.add_argument('--port', type=int, default=8000)
parser.add_argument('--log-level', default='info')
args = parser.parse_args()

uvicorn.run('app.main:app', host=args.host, port=args.port,
            log_level=args.log_level, reload=False)
