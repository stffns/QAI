#!/usr/bin/env python3
"""
Ejemplo de uso de QA Intelligence API Tools
============================================

Este script demuestra cómo usar las herramientas de testing de APIs
implementadas en QA Intelligence.

Uso:
    python ejemplo_api_tools.py

Herramientas incluidas:
- test_endpoint_raw(): Testing completo de endpoints
- health_check_raw(): Monitoreo de salud de servicios  
- performance_test_raw(): Testing de rendimiento
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(__file__))

from src.agent.tools.api_tools import test_endpoint_raw, health_check_raw, performance_test_raw
import json


def print_separator(title=""):
    """Imprime un separador visual"""
    print("\n" + "="*60)
    if title:
        print(f"🎯 {title}")
        print("="*60)


def print_result(result, title="Resultado"):
    """Imprime resultados de manera formateada"""
    print(f"\n📊 {title}:")
    print(f"   ✅ QA Status: {result.get('qa_status', 'N/A')}")
    print(f"   📈 QA Score: {result.get('qa_score', 0)}/100")
    print(f"   🔢 Status Code: {result.get('status_code', 'N/A')}")
    print(f"   🚀 Response Time: {result.get('response_time_ms', 0)}ms")
    
    # Mostrar issues si existen
    issues = result.get('qa_issues', [])
    if issues:
        print(f"   ⚠️  Issues: {', '.join(issues)}")
    
    # Mostrar recomendaciones
    recommendations = result.get('recommendations', [])
    if recommendations:
        print(f"   💡 Recommendations: {recommendations[0]}")


def main():
    """Función principal con ejemplos de uso"""
    
    print("🌐 QA INTELLIGENCE - API TOOLS DEMO")
    print("="*60)
    print("Demostrando las capacidades de testing de APIs...")
    
    try:
        # EJEMPLO 1: Testing básico de endpoint GET
        print_separator("EJEMPLO 1: Testing básico de API")
        print("🧪 Testeando GitHub API...")
        
        result1 = test_endpoint_raw("https://api.github.com/zen")
        print_result(result1, "GitHub API Test")
        
        # EJEMPLO 2: Health check de servicio
        print_separator("EJEMPLO 2: Health Check")
        print("🏥 Verificando salud del servicio...")
        
        health = health_check_raw("https://httpbin.org/status/200")
        print(f"\n💚 Health Check Result:")
        print(f"   🎯 Status: {health.get('status', 'N/A')}")
        print(f"   ⚡ Health Score: {health.get('health_score', 0)}/100")
        print(f"   ✅ Is Healthy: {health.get('is_healthy', False)}")
        print(f"   🕐 Response Time: {health.get('response_time_ms', 0)}ms")
        
        # EJEMPLO 3: Testing POST con datos
        print_separator("EJEMPLO 3: Testing POST con datos")
        print("📤 Enviando datos via POST...")
        
        post_data = {
            "name": "QA Engineer",
            "job": "API Testing",
            "tools": ["QA Intelligence", "API Tools"]
        }
        
        result3 = test_endpoint_raw(
            "https://httpbin.org/post",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=post_data
        )
        print_result(result3, "POST Test")
        
        # EJEMPLO 4: Performance testing
        print_separator("EJEMPLO 4: Performance Testing")
        print("📊 Ejecutando test de rendimiento (3 iteraciones)...")
        
        perf = performance_test_raw("https://httpbin.org/delay/0.2", iterations=3)
        
        print(f"\n📈 Performance Test Results:")
        print(f"   🎯 Success Rate: {perf.get('success_rate', 0)}%")
        print(f"   📊 Successful/Total: {perf.get('successful_requests', 0)}/{perf.get('iterations', 0)}")
        
        metrics = perf.get('performance_metrics', {})
        if metrics:
            print(f"   ⚡ Average: {metrics.get('avg_ms', 0):.0f}ms")
            print(f"   📊 Min/Max: {metrics.get('min_ms', 0):.0f}ms / {metrics.get('max_ms', 0):.0f}ms")
            print(f"   📈 P95: {metrics.get('p95_ms', 0):.0f}ms")
        
        qa_assessment = perf.get('qa_assessment', {})
        print(f"   🎯 QA Assessment: {qa_assessment.get('status', 'unknown')}")
        
        # EJEMPLO 5: Testing de error handling
        print_separator("EJEMPLO 5: Testing de errores")
        print("❌ Testeando endpoint que falla...")
        
        error_result = test_endpoint_raw("https://httpbin.org/status/500")
        print_result(error_result, "Error Test (500)")
        
        # EJEMPLO 6: Testing con timeout
        print_separator("EJEMPLO 6: Testing con timeout corto")
        print("⏱️  Testeando con timeout de 1 segundo...")
        
        timeout_result = test_endpoint_raw(
            "https://httpbin.org/delay/2", 
            timeout=1
        )
        print_result(timeout_result, "Timeout Test")
        
        # RESUMEN FINAL
        print_separator("RESUMEN")
        print("✅ Todos los ejemplos completados exitosamente!")
        print("\n🎯 Casos de uso demostrados:")
        print("   • Testing básico de endpoints GET")
        print("   • Health checks automáticos")  
        print("   • Testing POST con datos JSON")
        print("   • Performance testing con estadísticas")
        print("   • Manejo de errores HTTP")
        print("   • Testing con timeouts")
        
        print("\n💡 Próximos pasos:")
        print("   • Integrar con tus APIs reales")
        print("   • Configurar monitoreo automático")
        print("   • Usar en pipelines CI/CD")
        print("   • Crear dashboards de métricas")
        
    except Exception as e:
        print(f"\n❌ Error ejecutando ejemplos: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
