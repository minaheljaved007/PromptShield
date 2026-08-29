import os
import subprocess
import sys
import time


def main():
    port = os.getenv("PORT", "8000")

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ]
    )

    # Give FastAPI a moment to start before launching Gradio.
    time.sleep(3)

    frontend = subprocess.Popen(
        [
            sys.executable,
            "frontend/dashboard.py",
        ],
        env={
            **os.environ,
            "GRADIO_SERVER_PORT": "7860",
        },
    )

    try:
        backend.wait()
    finally:
        frontend.terminate()


if __name__ == "__main__":
    main()
