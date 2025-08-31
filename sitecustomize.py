"""Ensure backend directory is importable as 'app' when running from project root.

Python auto-imports sitecustomize if present on sys.path. Placing this at the
project root allows `pytest` and ad-hoc scripts (run from root) to resolve the
`app` package without manually exporting PYTHONPATH.
"""
import sys, pathlib
root = pathlib.Path(__file__).parent
backend = root / 'backend'
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))
