"""Launcher for PocketFriend.

Usage:
    python run.py                 # start the app on http://localhost:8501
    python run.py --port 9000     # use a different port
    python run.py --check-ai      # quick local AI check, no UI

Equivalent to: streamlit run app/main.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_ENTRY = PROJECT_ROOT / "app" / "main.py"


def run_app(port: int = 8501) -> int:
    """Start the Streamlit UI in a subprocess."""
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_ENTRY),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    print(f"Starting PocketFriend on http://localhost:{port}")
    try:
        return subprocess.call(command, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print("\nPocketFriend stopped.")
        return 0


def check_ai() -> int:
    """Print the local AI status. Handy for demos and troubleshooting."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from app import config, gemma  # noqa: E402

    print(f"Ollama host : {config.OLLAMA_HOST}")
    print(f"Model       : {config.OLLAMA_MODEL}")
    status = gemma.check_ollama()
    print(f"Ollama      : {'running' if status.ollama_running else 'not reachable'}")
    print(f"Model found : {'yes' if status.model_available else 'no'}")
    if status.local_models:
        print(f"Local models: {', '.join(status.local_models)}")
    if status.detail:
        print(f"Details     : {status.detail}")

    if not status.ready:
        print("\n" + status.user_message())
        return 1

    ok, reply = gemma.ping()
    print(f"Test reply  : {reply if ok else reply}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PocketFriend")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit port")
    parser.add_argument(
        "--check-ai", action="store_true", help="Check the local AI and exit"
    )
    args = parser.parse_args()

    if args.check_ai:
        return check_ai()
    return run_app(args.port)


if __name__ == "__main__":
    raise SystemExit(main())