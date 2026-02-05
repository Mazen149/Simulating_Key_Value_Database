"""Stress test utility that restarts the server repeatedly."""

from __future__ import annotations

import argparse
import subprocess
import threading
import time


def restart_loop(command: str, interval: float = 5.0) -> None:
    """Kill and restart process at regular intervals."""
    process = None
    try:
        while True:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                print(f"[{time.strftime('%H:%M:%S')}] Process terminated, restarting in {interval}s...")
                time.sleep(interval)

            print(f"[{time.strftime('%H:%M:%S')}] Starting process: {command}")
            process = subprocess.Popen(command, shell=True)
            process.wait()
            print(f"[{time.strftime('%H:%M:%S')}] Process exited unexpectedly")

    except KeyboardInterrupt:
        if process:
            process.terminate()
            process.wait()
        print("\nStopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Server Chaos Test Runner")
    parser.add_argument("--command", required=True, help="Command to execute")
    parser.add_argument("--interval", type=float, default=5.0, help="Restart interval in seconds")
    parser.add_argument("--restart", action="store_true", help="Enable automatic restart")
    args = parser.parse_args()

    if args.restart:
        restart_loop(args.command, args.interval)
    else:
        subprocess.run(args.command, shell=True)


if __name__ == "__main__":
    main()
