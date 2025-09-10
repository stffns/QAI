#!/usr/bin/env python3
"""
API REST simplificada para métricas de Prometheus - Frontend React.

Lee directamente las métricas de Prometheus sin usar la API de queries.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
import requests
import re
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="QA Intelligence Metrics API - Simplified",
    description="API REST simplificada para métricas de performance QA",
    version="1.0.0"
)

# CORS para React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URLs de métricas
PROMETHEUS_METRICS_URL = "http://localhost:9400/metrics"
ENDPOINT_METRICS_URL = "http://localhost:9401/metrics"

def parse_prometheus_metrics(metrics_text: str) -> Dict[str, List[Dict]]:
    """Parsea métricas de Prometheus desde texto."""
    metrics = {}
    lines = metrics_text.strip().split('\n')
    
    current_metric_name = None
    current_metric_type = None
    current_metric_help = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            if line.startswith('# HELP'):
                parts = line.split(' ', 3)
                if len(parts) >= 3:
                    current_metric_help = parts[2] if len(parts) == 3 else ' '.join(parts[3:])
                    current_metric_name = parts[2]
            elif line.startswith('# TYPE'):
                parts = line.split(' ', 3)
                if len(parts) >= 3:
                    current_metric_type = parts[3] if len(parts) > 3 else parts[2]
            continue
        
        # Parse metric line: metric_name{labels} value timestamp
        match = re.match(r'([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]*)\}\s+([^\s]+)(?:\s+([^\s]+))?', line)
        if not match:
            # Try simple metric without labels
            match = re.match(r'([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([^\s]+)(?:\s+([^\s]+))?', line)
            if match:
                metric_name = match.group(1)
                value = match.group(2)
                timestamp = match.group(3) if len(match.groups()) > 2 else None
                labels = {}
            else:
                continue
        else:
            metric_name = match.group(1)
            labels_str = match.group(2)
            value = match.group(3)
            timestamp = match.group(4)
            
            # Parse labels
            labels = {}
            if labels_str:
                for label_pair in labels_str.split(','):
                    if '=' in label_pair:
                        key, val = label_pair.split('=', 1)
                        labels[key.strip()] = val.strip('"')
        
        if metric_name not in metrics:
            metrics[metric_name] = []
        
        try:
            metrics[metric_name].append({
                'labels': labels,
                'value': float(value),
                'timestamp': float(timestamp) if timestamp else None
            })
        except ValueError:
            # Skip non-numeric values
            continue
    
    return metrics

@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "QA Intelligence Metrics API - Simplified",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics_sources": [PROMETHEUS_METRICS_URL, ENDPOINT_METRICS_URL]
    }

@app.get("/api/v1/executions/summary")
async def get_executions_summary():
    """Resumen de ejecuciones de performance tests."""
    try:
        response = requests.get(PROMETHEUS_METRICS_URL, timeout=10)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        
        # Extraer métricas de ejecuciones
        completed = 0
        failed = 0
        current_states = {}
        
        if 'qa_perf_executions_total' in metrics:
            for metric in metrics['qa_perf_executions_total']:
                status = metric['labels'].get('status', 'unknown')
                if status == 'COMPLETED':
                    completed = metric['value']
                elif status == 'FAILED':
                    failed = metric['value']
        
        if 'qa_perf_executions_current' in metrics:
            for metric in metrics['qa_perf_executions_current']:
                status = metric['labels'].get('status', 'unknown')
                current_states[status] = metric['value']
        
        return {
            "total_completed": completed,
            "total_failed": failed,
            "success_rate": (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0,
            "current_states": current_states,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting executions summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/endpoints/summary")
async def get_endpoints_summary():
    """Resumen de métricas por endpoint."""
    try:
        response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        
        # Organizar métricas por endpoint
        endpoints = {}
        
        metric_types = {
            'qa_perf_endpoint_requests_total': 'requests',
            'qa_perf_endpoint_p95_response_time_ms': 'p95_response_time',
            'qa_perf_endpoint_error_rate_percent': 'error_rate',
            'qa_perf_endpoint_rps': 'rps',
            'qa_perf_endpoint_performance_grade': 'performance_grade'
        }
        
        for metric_name, field_name in metric_types.items():
            if metric_name in metrics:
                for metric in metrics[metric_name]:
                    endpoint = metric['labels'].get('endpoint', 'unknown')
                    method = metric['labels'].get('method', 'unknown')
                    key = f"{method} {endpoint}"
                    
                    if key not in endpoints:
                        endpoints[key] = {
                            'endpoint': endpoint,
                            'method': method,
                            'metrics': {}
                        }
                    
                    endpoints[key]['metrics'][field_name] = metric['value']
        
        return {
            "endpoints": list(endpoints.values()),
            "total_endpoints": len(endpoints),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting endpoints summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/endpoints/problems")
async def get_endpoint_problems():
    """Detecta endpoints con problemas."""
    try:
        response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        problems = []
        
        # High error rate (>5%)
        if 'qa_perf_endpoint_error_rate_percent' in metrics:
            for metric in metrics['qa_perf_endpoint_error_rate_percent']:
                if metric['value'] > 5:
                    problems.append({
                        "type": "high_error_rate",
                        "severity": "critical" if metric['value'] > 50 else "warning",
                        "endpoint": metric['labels'].get('endpoint', 'unknown'),
                        "method": metric['labels'].get('method', 'unknown'),
                        "value": metric['value'],
                        "threshold": 5.0,
                        "message": f"Error rate {metric['value']:.1f}% exceeds threshold"
                    })
        
        # Slow response time (>1000ms)
        if 'qa_perf_endpoint_p95_response_time_ms' in metrics:
            for metric in metrics['qa_perf_endpoint_p95_response_time_ms']:
                if metric['value'] > 1000:
                    problems.append({
                        "type": "slow_response",
                        "severity": "critical" if metric['value'] > 2000 else "warning",
                        "endpoint": metric['labels'].get('endpoint', 'unknown'),
                        "method": metric['labels'].get('method', 'unknown'),
                        "value": metric['value'],
                        "threshold": 1000.0,
                        "message": f"P95 response time {metric['value']:.0f}ms exceeds threshold"
                    })
        
        return {
            "problems": problems,
            "total_problems": len(problems),
            "critical_problems": len([p for p in problems if p['severity'] == 'critical']),
            "warning_problems": len([p for p in problems if p['severity'] == 'warning']),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error detecting problems: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/endpoints/{endpoint_name}")
async def get_endpoint_detail(endpoint_name: str, method: Optional[str] = None):
    """Detalles de un endpoint específico."""
    try:
        response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        
        endpoint_data = {
            'endpoint': endpoint_name,
            'method': method,
            'metrics': {}
        }
        
        metric_types = {
            'qa_perf_endpoint_requests_total': 'requests',
            'qa_perf_endpoint_p95_response_time_ms': 'p95_response_time',
            'qa_perf_endpoint_error_rate_percent': 'error_rate',
            'qa_perf_endpoint_rps': 'rps',
            'qa_perf_endpoint_performance_grade': 'performance_grade'
        }
        
        for metric_name, field_name in metric_types.items():
            if metric_name in metrics:
                for metric in metrics[metric_name]:
                    if (metric['labels'].get('endpoint') == endpoint_name and
                        (method is None or metric['labels'].get('method') == method)):
                        endpoint_data['metrics'][field_name] = metric['value']
        
        return endpoint_data
        
    except Exception as e:
        logger.error(f"Error getting endpoint detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics/raw")
async def get_raw_metrics():
    """Métricas raw de Prometheus."""
    try:
        prometheus_response = requests.get(PROMETHEUS_METRICS_URL, timeout=10)
        endpoint_response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        
        return {
            "prometheus_metrics": parse_prometheus_metrics(prometheus_response.text),
            "endpoint_metrics": parse_prometheus_metrics(endpoint_response.text),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting raw metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting QA Intelligence Metrics API - Simplified")
    print(f"📊 Prometheus Metrics: {PROMETHEUS_METRICS_URL}")
    print(f"🎯 Endpoint Metrics: {ENDPOINT_METRICS_URL}")
    print("🌐 API will be available at: http://localhost:8003")
    print("📚 API docs at: http://localhost:8003/docs")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8003,
        log_level="info"
    )
