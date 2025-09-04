#!/usr/bin/env python3
"""
Cliente de prueba de velocidad - Test aislado para verificar tiempos de respuesta optimizados
"""

import asyncio
import json
import websockets
import time
from datetime import datetime

async def test_client():
    """Cliente de prueba para medir velocidad real"""
    
    print("⚡ CLIENTE DE PRUEBA DE VELOCIDAD")
    print("=" * 50)
    print("🎯 Objetivo: Respuestas < 10 segundos")
    print("🔗 Servidor: ws://127.0.0.1:8765")
    print("=" * 50)
    
    try:
        # Dar tiempo al servidor para inicializar
        await asyncio.sleep(1)
        
        async with websockets.connect("ws://127.0.0.1:8765") as websocket:
            print("✅ Conectado al servidor WebSocket")
            
            # Test simple y directo
            message = "Hola"
            print(f"\n⚡ Enviando mensaje: '{message}'")
            
            # Timing preciso
            start_time = time.time()
            
            # Enviar mensaje en formato correcto del WebSocketEnvelope
            envelope = {
                "type": "chat_message",
                "version": "2.0",
                "payload": {
                    "message_type": "chat_message",
                    "content": message,
                    "attachments": None,
                    "metadata": None,
                    "language": None,
                    "locale": None,
                    "timestamp": None
                },
                "session_id": "speed_test_123",
                "user_id": "speed_test_user",
                "correlation_id": None
            }
            
            await websocket.send(json.dumps(envelope))
            print(f"📤 Mensaje enviado: {time.time() - start_time:.3f}s")
            
            # Recibir respuesta con timeout
            try:
                print("⏳ Esperando respuesta...")
                response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                end_time = time.time()
                
                response_time = end_time - start_time
                
                # Analizar respuesta
                try:
                    response_data = json.loads(response)
                    print(f"📥 Respuesta recibida: {response_time:.2f}s")
                    
                    if 'payload' in response_data and 'content' in response_data['payload']:
                        agent_response = response_data['payload']['content']
                        response_length = len(agent_response)
                        
                        # Evaluar performance
                        if response_time <= 5:
                            status = "🚀 EXCELENTE"
                        elif response_time <= 10:
                            status = "✅ BUENO"
                        elif response_time <= 15:
                            status = "⚠️ ACEPTABLE"
                        else:
                            status = "❌ LENTO"
                        
                        print(f"⏱️ Tiempo: {response_time:.2f}s {status}")
                        print(f"📝 Longitud: {response_length} caracteres")
                        print(f"🤖 Respuesta: {agent_response[:150]}{'...' if len(agent_response) > 150 else ''}")
                        
                        # Comparación con baseline
                        print(f"\n📊 COMPARACIÓN:")
                        print(f"   Antes (con reasoning): 101 segundos ❌")
                        print(f"   Ahora (optimizado): {response_time:.2f} segundos {status}")
                        improvement = ((101 - response_time) / 101) * 100
                        print(f"   Mejora: {improvement:.1f}% 🎯")
                        
                    else:
                        print(f"📋 Respuesta técnica: {response_data}")
                        
                except json.JSONDecodeError:
                    print(f"📋 Respuesta raw: {response[:200]}...")
                
            except asyncio.TimeoutError:
                print("⏰ ❌ TIMEOUT - Respuesta > 20 segundos")
                print("🔍 El servidor puede estar sobrecargado")
            
            print("\n" + "=" * 50)
            print("✅ TEST DE VELOCIDAD COMPLETADO")
            print("=" * 50)
    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("🔍 Verifica que el servidor esté corriendo en ws://127.0.0.1:8765")

if __name__ == "__main__":
    asyncio.run(test_client())
