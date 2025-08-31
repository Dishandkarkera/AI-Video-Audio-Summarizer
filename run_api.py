"""Convenience launcher for FastAPI server from project root.
Usage:
  python run_api.py --port 8000 --host 127.0.0.1

Ensures the backend/ directory is added to sys.path so 'app' package resolves.
"""
import sys, argparse, pathlib, uvicorn

ROOT = pathlib.Path(__file__).parent.resolve()
BACKEND_DIR = ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--host', default='127.0.0.1')
  parser.add_argument('--port', type=int, default=8000)
  parser.add_argument('--reload', action='store_true')
  args = parser.parse_args()

  uvicorn.run('app.main:app', host=args.host, port=args.port, reload=args.reload)


if __name__ == '__main__':
  # Windows (spawn) safe entrypoint for uvicorn reload / multiprocessing
  main()
