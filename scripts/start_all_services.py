#!/usr/bin/env python3
"""
QA Intelligence Complete Services Manager

Maneja todos los servicios necesarios para la integración Prometheus + React:
1. Prometheus Exporter (9400) - Métricas generales
2. Endpoint Exporter (9401) - Métricas por endpoint 
3. REST API (8003) - Bridge para React
4. WebSocket Server (8765) - Comunicación tiempo real
"""

import signal
import socket
import subprocess
import sys
import time
import threading
from pathlib import Path
import urllib.request
import urllib.error

class ServiceManager:
    def __init__(self):
        self.services = []
        self.running = True
        
    def start_service(self, name: str, command: list, cwd: Path = None) -> subprocess.Popen:
        """Start a service subprocess."""
        print(f"🚀 Starting {name}...")
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd or Path.cwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return process
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return None

    def monitor_service(self, name: str, process: subprocess.Popen):
        """Monitor a service and log its output."""
        def log_output(stream, prefix):
            for line in iter(stream.readline, ''):
                if line.strip() and self.running:
                    print(f"[{prefix}] {line.strip()}")
            stream.close()
        
        if process:
            threading.Thread(
                target=log_output, 
                args=(process.stdout, name), 
                daemon=True
            ).start()
            threading.Thread(
                target=log_output, 
                args=(process.stderr, f"{name}-ERR"), 
                daemon=True
            ).start()

    def wait_for_service(self, name: str, url: str, timeout: int = 60) -> bool:
        """Wait for a service to be ready with special WebSocket handling."""
        print(f"⏳ Waiting for {name} to be ready at {url}...")
        start_time = time.time()
        
        # Special handling for WebSocket to avoid handshake errors
        if "WebSocket" in name:
            while time.time() - start_time < timeout:
                try:
                    # Check if port 8765 is listening
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', 8765))
                    sock.close()
                    if result == 0:  # Port is open
                        print(f"✅ {name} is ready at {url}")
                        return True
                except Exception:
                    pass
                time.sleep(2)
        else:
            # Standard HTTP checking for other services
            while time.time() - start_time < timeout:
                try:
                    with urllib.request.urlopen(url, timeout=5) as response:
                        if response.status == 200:
                            print(f"✅ {name} is ready at {url}")
                            return True
                except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError, OSError):
                    pass  # Expected during startup
                time.sleep(2)
        
        print(f"❌ {name} failed to start within {timeout} seconds")
        return False

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down all services...")
        self.running = False
        
        for name, process in reversed(self.services):  # Stop in reverse order
            if process and process.poll() is None:
                print(f"⏹️  Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    print(f"✅ {name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"💀 Force killing {name}...")
                    process.kill()
                    process.wait()
        
        print("🎉 All services stopped")
        sys.exit(0)

    def start_all_services(self):
        """Start all QA Intelligence services."""
        print("🌐 QA Intelligence Complete Services Manager")
        print("=" * 50)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 1. Start Prometheus Exporter (9400)
        prometheus_process = self.start_service(
            "Prometheus Exporter",
            [sys.executable, "-m", "src.observability.prometheus_exporter"]
        )
        if prometheus_process:
            self.services.append(("Prometheus Exporter", prometheus_process))
            self.monitor_service("Prometheus", prometheus_process)
        
        # 2. Start Endpoint Exporter (9401)
        endpoint_process = self.start_service(
            "Endpoint Exporter",
            [sys.executable, "-m", "src.observability.prometheus_endpoint_exporter"]
        )
        if endpoint_process:
            self.services.append(("Endpoint Exporter", endpoint_process))
            self.monitor_service("Endpoint", endpoint_process)
        
        # Wait a bit for exporters to initialize
        time.sleep(3)
        
        # 3. Start REST API (8003)
        api_process = self.start_service(
            "REST API",
            [sys.executable, "src/api/metrics_api.py"]
        )
        if api_process:
            self.services.append(("REST API", api_process))
            self.monitor_service("API", api_process)
        
        # 4. Start WebSocket Server (8765)
        websocket_process = self.start_service(
            "WebSocket Server", 
            [sys.executable, "run_websocket_server.py"]
        )
        if websocket_process:
            self.services.append(("WebSocket Server", websocket_process))
            self.monitor_service("WebSocket", websocket_process)
        
        # Wait for all services to be ready
        print("\n⏳ Checking service readiness...")
        time.sleep(3)  # Give services time to start
        
        # Check each service
        service_checks = [
            ("Prometheus Exporter", "http://localhost:9400/metrics"),
            ("Endpoint Exporter", "http://localhost:9401/metrics"),
            ("REST API", "http://localhost:8003/"),
            ("WebSocket Server", "ws://localhost:8765/")
        ]
        
        ready_services = 0
        for name, url in service_checks:
            if self.wait_for_service(name, url, timeout=15):
                ready_services += 1
        
        print(f"\n📊 SERVICE STATUS: {ready_services}/{len(service_checks)} ready")
        print("=" * 50)
        
        if ready_services >= 3:  # At least 3 services (WebSocket might not respond to HTTP)
            print("🎉 QA Intelligence Stack Ready!")
            print()
            print("📊 AVAILABLE SERVICES:")
            print("  🔢 Prometheus Metrics: http://localhost:9400/metrics")
            print("  🎯 Endpoint Metrics:   http://localhost:9401/metrics") 
            print("  🌐 REST API:           http://localhost:8003/")
            print("  📚 API Documentation: http://localhost:8003/docs")
            print("  🔌 WebSocket Server:   ws://localhost:8765")
            print()
            print("🚀 REACT INTEGRATION:")
            print("  📁 Use hooks from: examples/react_frontend_integration.js")
            print("  🌐 API Base URL: http://localhost:8003")
            print()
            print("💡 All systems ready for React frontend integration!")
            print("   Press Ctrl+C to stop all services")
        else:
            print("❌ Critical services failed to start")
            self.signal_handler(signal.SIGTERM, None)
            return 1
        
        # Keep main thread alive and monitor services
        try:
            while self.running:
                # Check if any critical service died
                for name, process in self.services:
                    if process.poll() is not None:
                        print(f"❌ {name} has stopped unexpectedly (exit code: {process.returncode})")
                        if name in ["Prometheus Exporter", "REST API"]:  # Critical services
                            print("🚨 Critical service failed - shutting down")
                            self.signal_handler(signal.SIGTERM, None)
                            return 1
                        else:
                            print(f"⚠️  {name} failed but continuing with other services")
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)
        
        return 0

def main():
    """Main entry point."""
    manager = ServiceManager()
    return manager.start_all_services()

if __name__ == "__main__":
    sys.exit(main())
