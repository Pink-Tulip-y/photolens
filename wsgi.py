"""Production WSGI entry point — use with gunicorn: `gunicorn wsgi:app`"""
from app import app

if __name__ == "__main__":
    app.run()
