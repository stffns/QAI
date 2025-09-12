#!/usr/bin/env python3
"""
Test de diagnóstico avanzado para problemas intermitentes de WebSocket
"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime
import time

class WebSocketDiagnosticTest:
    def __init__(self):
        self.uri = "ws://127.0.0.1:8765"
        self.test_results = []
        
    async def test_scenario(self, message, scenario_name, expected_behavior="streaming"):
        """Test individual scenario and capture detailed results"""
        print(f"\n🧪 Scenario: {scenario_name}")
        print("=" * 60)
        
        start_time = time.time()
        result = {
            "scenario": scenario_name,
            "message": message,
            "start_time": start_time,
            "responses": [],
            "success": False,
            "error": None,
            "total_time": 0,
            "chunks_received": 0,
            "stream_complete": False
        }
        
        try:
            async with websockets.connect(self.uri) as websocket:
                # Send message
                test_message = {
                    "type": "chat_message",
                    "version": "2.0",
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": f"test_{scenario_name.lower().replace(' ', '_')}",
                    "user_id": "diagnostic_test",
                    "payload": {
                        "message_type": "chat_message",
                        "content": message,
                        "metadata": {"test_scenario": scenario_name}
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                print(f"📤 Message sent: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                
                # Collect responses with timeout
                timeout = 30
                response_count = 0
                stream_started = False
                stream_ended = False
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_count += 1
                        
                        try:
                            response_data = json.loads(response)
                            message_type = response_data.get("type", "unknown")
                            result["responses"].append({
                                "index": response_count,
                                "type": message_type,
                                "timestamp": time.time(),
                                "data": response_data
                            })
                            
                            if message_type == "system_event":
                                print(f"   ℹ️  #{response_count}: System event")
                                
                            elif message_type == "agent_response_stream_start":
                                stream_started = True
                                print(f"   🚀 #{response_count}: Stream started")
                                
                            elif message_type == "agent_response_stream_chunk":
                                payload = response_data.get("payload", {})
                                chunk = payload.get("chunk", "")
                                chunk_index = payload.get("chunk_index", 0)
                                result["chunks_received"] += 1
                                print(f"   📦 #{response_count}: Chunk {chunk_index}: '{chunk[:30]}{'...' if len(chunk) > 30 else ''}'")
                                
                            elif message_type == "agent_response_stream_end":
                                stream_ended = True
                                payload = response_data.get("payload", {})
                                total_chunks = payload.get("total_chunks", 0)
                                print(f"   🏁 #{response_count}: Stream ended ({total_chunks} chunks)")
                                result["stream_complete"] = True
                                break
                                
                            elif message_type == "agent_response":
                                # Non-streaming response
                                content = response_data.get("payload", {}).get("content", "")
                                print(f"   💬 #{response_count}: Direct response: '{content[:50]}{'...' if len(content) > 50 else ''}'")
                                result["stream_complete"] = True
                                break
                                
                            elif message_type == "error_event":
                                payload = response_data.get("payload", {})
                                error_code = payload.get("error_code", "unknown")
                                error_message = payload.get("error_message", "unknown")
                                print(f"   ❌ #{response_count}: Error: {error_code} - {error_message}")
                                result["error"] = f"{error_code}: {error_message}"
                                break
                                
                            else:
                                print(f"   ❓ #{response_count}: Unknown type: {message_type}")
                            
                            # Safety timeout
                            if time.time() - start_time > timeout:
                                print(f"   ⏰ Timeout reached ({timeout}s)")
                                result["error"] = "Timeout"
                                break
                                
                        except json.JSONDecodeError as e:
                            print(f"   ⚠️  #{response_count}: JSON decode error: {e}")
                            result["error"] = f"JSON decode error: {e}"
                            
                    except asyncio.TimeoutError:
                        print(f"   ⏰ No response after 10s (received {response_count} responses)")
                        if not stream_started:
                            result["error"] = "No stream started"
                        elif stream_started and not stream_ended:
                            result["error"] = "Stream started but never ended"
                        break
                        
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            result["error"] = f"Connection error: {e}"
        
        # Calculate results
        result["total_time"] = time.time() - start_time
        result["success"] = result["stream_complete"] and result["error"] is None
        
        # Summary
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"\n📊 {status}")
        print(f"   ⏱️  Time: {result['total_time']:.2f}s")
        print(f"   📨 Responses: {len(result['responses'])}")
        print(f"   📦 Chunks: {result['chunks_received']}")
        print(f"   🏁 Complete: {result['stream_complete']}")
        if result["error"]:
            print(f"   ❌ Error: {result['error']}")
        
        self.test_results.append(result)
        return result
    
    async def run_diagnostic_suite(self):
        """Run comprehensive diagnostic tests"""
        print("🔍 WebSocket Intermittent Issues Diagnostic")
        print("=" * 80)
        
        # Test scenarios that might behave differently
        scenarios = [
            ("Hola", "Simple Greeting"),
            ("¿Qué aplicaciones están disponibles?", "App Query"),
            ("Ejecuta una prueba de performance de EVA con 2 RPS por 30 segundos", "Performance Test Command"),
            ("Explícame el estado actual del sistema de QA", "Complex Analysis"),
            ("OK", "Very Short Response"),
            ("Dime algo interesante sobre testing de performance y las mejores prácticas para QA", "Long Response Request"),
            ("¿Cuáles son las últimas ejecuciones?", "Recent Executions Query"),
            ("Help", "Help Command"),
        ]
        
        for message, scenario_name in scenarios:
            await self.test_scenario(message, scenario_name)
            await asyncio.sleep(2)  # Brief pause between tests
        
        # Summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive diagnostic report"""
        print("\n" + "=" * 80)
        print("📋 DIAGNOSTIC SUMMARY REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - successful_tests
        
        print(f"🎯 Overall Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['scenario']}: {result['error']}")
                    print(f"     Time: {result['total_time']:.2f}s, Responses: {len(result['responses'])}, Chunks: {result['chunks_received']}")
        
        print(f"\n✅ SUCCESSFUL TESTS ({successful_tests}):")
        for result in self.test_results:
            if result["success"]:
                print(f"   • {result['scenario']}: {result['total_time']:.2f}s, {result['chunks_received']} chunks")
        
        # Pattern analysis
        print(f"\n🔍 PATTERN ANALYSIS:")
        avg_time_success = sum(r["total_time"] for r in self.test_results if r["success"]) / max(successful_tests, 1)
        avg_time_failed = sum(r["total_time"] for r in self.test_results if not r["success"]) / max(failed_tests, 1)
        
        print(f"   📊 Average time (successful): {avg_time_success:.2f}s")
        if failed_tests > 0:
            print(f"   📊 Average time (failed): {avg_time_failed:.2f}s")
        
        # Error patterns
        error_types = {}
        for result in self.test_results:
            if result["error"]:
                error_type = result["error"].split(":")[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if error_types:
            print(f"\n🚨 ERROR PATTERNS:")
            for error_type, count in error_types.items():
                print(f"   • {error_type}: {count} occurrences")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if failed_tests == 0:
            print("   ✅ WebSocket appears to be working consistently")
            print("   💭 If frontend issues persist, check client-side message handling")
        elif failed_tests < total_tests // 2:
            print("   ⚠️  Intermittent issues detected - investigate timing or load-related causes")
            print("   🔧 Consider implementing retry logic in frontend")
        else:
            print("   🚨 Significant issues detected - requires immediate investigation")
            print("   🔍 Check server logs for detailed error information")

async def main():
    """Run diagnostic test suite"""
    diagnostic = WebSocketDiagnosticTest()
    await diagnostic.run_diagnostic_suite()

if __name__ == "__main__":
    asyncio.run(main())
