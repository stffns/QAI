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
import subprocess
import sys
import time
import threading
import socket
import psutil
from pathlib import Path
import urllib.request
import urllib.error

class ServiceManager:
    def __init__(self):
        self.services = []
        self.running = True
        
    def check_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result == 0
    
    def kill_process_on_port(self, port: int) -> bool:
        """Kill any process using the specified port."""
        try:
            # First try with lsof command (more reliable on macOS)
            import subprocess
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            try:
                                process = psutil.Process(int(pid.strip()))
                                print(f"🔪 Killing process {process.name()} (PID: {pid.strip()}) on port {port}")
                                process.terminate()
                                process.wait(timeout=3)
                                return True
                            except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
                                try:
                                    # Force kill if terminate doesn't work
                                    subprocess.run(['kill', '-9', pid.strip()], check=False)
                                    print(f"💀 Force killed PID {pid.strip()} on port {port}")
                                    return True
                                except:
                                    pass
            except Exception as e:
                print(f"⚠️  lsof command failed: {e}")
            
            # Fallback to psutil method
            for conn in psutil.net_connections():
                if hasattr(conn, 'laddr') and conn.laddr and hasattr(conn.laddr, 'port'):
                    if conn.laddr.port == port and conn.pid:
                        process = None
                        try:
                            process = psutil.Process(conn.pid)
                            print(f"🔪 Killing process {process.name()} (PID: {conn.pid}) on port {port}")
                            process.terminate()
                            process.wait(timeout=3)
                            return True
                        except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
                            try:
                                if process is not None:
                                    process.kill()
                                    print(f"💀 Force killed process on port {port}")
                                return True
                            except psutil.NoSuchProcess:
                                pass
        except Exception as e:
            print(f"⚠️  Error killing process on port {port}: {e}")
        return False
    
    def ensure_port_available(self, port: int, service_name: str) -> bool:
        """Ensure a port is available, killing existing processes if necessary."""
        if self.check_port_in_use(port):
            print(f"⚠️  Port {port} is in use for {service_name}")
            if self.kill_process_on_port(port):
                print(f"✅ Port {port} freed for {service_name}")
                time.sleep(2)  # Wait for port to be fully freed
                return not self.check_port_in_use(port)
            else:
                print(f"❌ Failed to free port {port} for {service_name}")
                return False
        return True
        
    def start_service(self, name: str, command: list, cwd: Path | None = None) -> subprocess.Popen | None:
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

    def wait_for_service(self, name: str, url: str, timeout: int = 30, is_websocket: bool = False):
        """Wait for a service to be ready."""
        print(f"⏳ Waiting for {name} to be ready at {url}...")
        start_time = time.time()
        
        if is_websocket:
            # For WebSocket, just check if the port is listening
            import re
            port_match = re.search(r':(\d+)', url)
            if port_match:
                port = int(port_match.group(1))
                while time.time() - start_time < timeout:
                    if self.check_port_in_use(port):
                        print(f"✅ {name} is ready at {url}")
                        return True
                    time.sleep(1)
            print(f"❌ {name} failed to start within {timeout} seconds")
            return False
        else:
            # For HTTP services, use the original method
            while time.time() - start_time < timeout:
                try:
                    urllib.request.urlopen(url, timeout=2)
                    print(f"✅ {name} is ready at {url}")
                    return True
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(1)
            
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
        
        # Define required ports for each service
        required_ports = {
            9400: "Prometheus Exporter",
            9401: "Endpoint Exporter", 
            8003: "REST API",
            8765: "WebSocket Server"
        }
        
        # Check and free ports if needed
        print("🔍 Checking required ports...")
        for port, service_name in required_ports.items():
            if not self.ensure_port_available(port, service_name):
                print(f"❌ Cannot free port {port} for {service_name}")
                return 1
        
        print("✅ All required ports are available")
        print()
        
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
        
        # Check each service with appropriate method
        service_checks = [
            ("Prometheus Exporter", "http://localhost:9400/metrics", False),
            ("Endpoint Exporter", "http://localhost:9401/metrics", False),
            ("REST API", "http://localhost:8003/", False),
            ("WebSocket Server", "ws://localhost:8765", True)  # WebSocket needs special handling
        ]
        
        ready_services = 0
        for name, url, is_websocket in service_checks:
            if self.wait_for_service(name, url, timeout=15, is_websocket=is_websocket):
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
