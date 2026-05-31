"""PhotoLens Production Launcher (Windows-compatible)
Uses waitress WSGI server — gunicorn is Unix-only.
Usage: python run_prod.py
"""
import os
import sys

from waitress import serve
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    threads = int(os.environ.get("THREADS", 4))

    print(f"[PhotoLens] Starting production server on {host}:{port} (waitress, {threads} threads)")
    print(f"[PhotoLens] Open http://localhost:{port} in your browser")
    print(f"[PhotoLens] Press Ctrl+C to stop")
    sys.stdout.flush()

    serve(app, host=host, port=port, threads=threads, channel_timeout=120)
