#!/usr/bin/env python3
"""
QA Intelligence Services Manager

Utility script to manage WebSocket Server and Prometheus Exporter together.
Ensures both services start/stop together and handles graceful shutdown.
"""

import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


def start_service(name: str, command: list, cwd: Path = None) -> subprocess.Popen:
    """Start a service subprocess."""
    print(f"🚀 Starting {name}...")
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd or Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None


def monitor_service(name: str, process: subprocess.Popen):
    """Monitor a service and log its output."""

    def log_output(stream, prefix):
        for line in iter(stream.readline, ""):
            if line.strip():
                print(f"[{prefix}] {line.strip()}")
        stream.close()

    if process:
        # Start threads to handle stdout and stderr
        threading.Thread(
            target=log_output, args=(process.stdout, name), daemon=True
        ).start()
        threading.Thread(
            target=log_output, args=(process.stderr, f"{name}-ERR"), daemon=True
        ).start()


def wait_for_service(name: str, url: str, timeout: int = 30):
    """Wait for a service to be ready."""
    import urllib.error
    import urllib.request

    print(f"⏳ Waiting for {name} to be ready at {url}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"✅ {name} is ready at {url}")
            return True
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1)

    print(f"❌ {name} failed to start within {timeout} seconds")
    return False


def main():
    """Main service manager."""
    print("🌐 QA Intelligence Services Manager")
    print("=" * 40)

    services = []

    def signal_handler(signum, frame):
        print("\n🛑 Shutting down services...")
        for name, process in services:
            if process and process.poll() is None:
                print(f"⏹️  Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start Prometheus Exporter
    prometheus_process = start_service(
        "Prometheus Exporter",
        [sys.executable, "-m", "src.observability.prometheus_exporter"],
    )
    if prometheus_process:
        services.append(("Prometheus Exporter", prometheus_process))
        monitor_service("Prometheus", prometheus_process)

    # Start WebSocket Server
    websocket_process = start_service(
        "WebSocket Server", [sys.executable, "run_websocket_server.py"]
    )
    if websocket_process:
        services.append(("WebSocket Server", websocket_process))
        monitor_service("WebSocket", websocket_process)

    # Wait for services to be ready
    time.sleep(2)  # Give services time to start

    prometheus_ready = wait_for_service(
        "Prometheus", "http://localhost:9400/metrics", timeout=10
    )

    websocket_ready = wait_for_service(
        "WebSocket Server", "http://localhost:8765", timeout=10
    )

    if prometheus_ready and websocket_ready:
        print("\n🎉 All services are ready!")
        print("📊 Prometheus metrics: http://localhost:9400/metrics")
        print("🌐 WebSocket server: ws://localhost:8765")
        print("💡 Ready for Grafana integration!")
        print("\nPress Ctrl+C to stop all services")
    else:
        print("\n❌ Some services failed to start properly")
        signal_handler(signal.SIGTERM, None)
        return 1

    # Keep main thread alive
    try:
        while True:
            # Check if any service died
            for name, process in services:
                if process.poll() is not None:
                    print(f"❌ {name} has stopped unexpectedly")
                    signal_handler(signal.SIGTERM, None)
                    return 1
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    sys.exit(main())
