const http = require('http');
const https = require('https');

console.log('🧪 PROBANDO TODOS LOS ENDPOINTS QA INTELLIGENCE');
console.log('==================================================\n');

// Helper para hacer requests HTTP
function makeRequest(url, method = 'GET') {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const client = urlObj.protocol === 'https:' ? https : http;

        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname + urlObj.search,
            method: method,
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'QAI-Test-Client'
            }
        };

        const req = client.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                resolve({
                    status: res.statusCode,
                    headers: res.headers,
                    body: data
                });
            });
        });

        req.on('error', error => reject(error));
        req.end();
    });
}

// Helper para mostrar resultados
function showResult(name, url, result) {
    const status = result.status;
    const emoji = status === 200 ? '✅' : status < 400 ? '⚠️' : '❌';

    console.log(`${emoji} ${name}`);
    console.log(`   URL: ${url}`);
    console.log(`   Status: ${status}`);

    // Mostrar contenido relevante
    if (result.body) {
        try {
            const jsonData = JSON.parse(result.body);
            console.log(`   Tipo: JSON`);
            if (jsonData.message) console.log(`   Mensaje: ${jsonData.message}`);
            if (jsonData.timestamp) console.log(`   Timestamp: ${jsonData.timestamp}`);
            if (jsonData.metrics) console.log(`   Métricas: ${Object.keys(jsonData.metrics).length} elementos`);
            if (jsonData.data) console.log(`   Data: ${Array.isArray(jsonData.data) ? jsonData.data.length + ' elementos' : 'objeto'}`);
            if (jsonData.execution) {
                console.log(`   Execution: ${jsonData.execution.execution_name || jsonData.execution.execution_id || 'N/A'}`);
                if (jsonData.execution.status) console.log(`   Status: ${jsonData.execution.status}`);
            }
            if (jsonData.endpoints && Array.isArray(jsonData.endpoints)) {
                console.log(`   Endpoints: ${jsonData.endpoints.length} endpoints`);
            }
            if (jsonData.endpoints_summary) {
                console.log(`   Endpoints Summary: ${jsonData.endpoints_summary.total_endpoints} endpoints`);
            }
            if (jsonData.problems) {
                console.log(`   Problems: ${jsonData.problems.length} issues detected`);
            }
        } catch {
            if (result.body.includes('# HELP')) {
                const lines = result.body.split('\n').filter(line => line.startsWith('# HELP'));
                console.log(`   Tipo: Prometheus Metrics`);
                console.log(`   Métricas: ${lines.length} métricas disponibles`);
                if (lines.length > 0) {
                    console.log(`   Ejemplos: ${lines.slice(0, 3).map(line => line.split(' ')[2]).join(', ')}`);
                }
            } else if (result.body.includes('<!DOCTYPE html>')) {
                console.log(`   Tipo: HTML`);
                const title = result.body.match(/<title>(.*?)<\/title>/);
                if (title) console.log(`   Título: ${title[1]}`);
            } else {
                console.log(`   Tipo: Text`);
                console.log(`   Tamaño: ${result.body.length} caracteres`);
                const preview = result.body.substring(0, 100);
                console.log(`   Preview: ${preview}${result.body.length > 100 ? '...' : ''}`);
            }
        }
    }
    console.log('');
}

async function testEndpoints() {
    const endpoints = [
        // 1. Prometheus Metrics (Puerto 9400)
        {
            name: 'Prometheus Principal',
            url: 'http://localhost:9400/metrics',
            description: 'Métricas principales de ejecuciones'
        },

        // 2. Endpoint Metrics (Puerto 9401)
        {
            name: 'Prometheus Endpoints',
            url: 'http://localhost:9401/metrics',
            description: 'Métricas detalladas por endpoint'
        },

        // 3. REST API (Puerto 8003)
        {
            name: 'API Root',
            url: 'http://localhost:8003/',
            description: 'Punto de entrada principal'
        },
        {
            name: 'API Health',
            url: 'http://localhost:8003/health',
            description: 'Estado de salud del API'
        },
        {
            name: 'API Docs',
            url: 'http://localhost:8003/docs',
            description: 'Documentación automática'
        },

        // 4. API V1 Endpoints (Corregidos)
        {
            name: 'Executions Summary',
            url: 'http://localhost:8003/api/v1/executions/summary',
            description: 'Resumen de ejecuciones'
        },
        {
            name: 'Executions Recent',
            url: 'http://localhost:8003/api/v1/executions/recent',
            description: 'Última ejecución con resumen'
        },
        {
            name: 'Endpoints Summary',
            url: 'http://localhost:8003/api/v1/endpoints/summary',
            description: 'Resumen de métricas por endpoint'
        },
        {
            name: 'Endpoint Problems',
            url: 'http://localhost:8003/api/v1/endpoints/problems',
            description: 'Detectar endpoints con problemas'
        },
        {
            name: 'Raw Metrics',
            url: 'http://localhost:8003/api/v1/metrics/raw',
            description: 'Métricas raw de Prometheus'
        }
    ];

    console.log(`Probando ${endpoints.length} endpoints...\n`);

    let passed = 0;
    let failed = 0;

    for (const endpoint of endpoints) {
        try {
            console.log(`🔍 Probando: ${endpoint.name}`);
            console.log(`   Descripción: ${endpoint.description}`);

            const result = await makeRequest(endpoint.url);
            showResult(endpoint.name, endpoint.url, result);

            if (result.status === 200) {
                passed++;
            } else {
                failed++;
            }
        } catch (error) {
            console.log(`❌ ${endpoint.name}`);
            console.log(`   URL: ${endpoint.url}`);
            console.log(`   Error: ${error.message}`);
            console.log('');
            failed++;
        }

        // Pequeña pausa entre requests
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    console.log('==================================================');
    console.log('📊 RESUMEN DE PRUEBAS');
    console.log('==================================================');
    console.log(`✅ Exitosos: ${passed}`);
    console.log(`❌ Fallidos: ${failed}`);
    console.log(`📊 Total: ${endpoints.length}`);
    console.log(`🎯 Éxito: ${Math.round((passed / endpoints.length) * 100)}%`);

    if (failed === 0) {
        console.log('\n🎉 ¡TODOS LOS ENDPOINTS FUNCIONANDO CORRECTAMENTE!');
        console.log('✅ Tu stack está listo para React');
    } else {
        console.log(`\n⚠️  ${failed} endpoint(s) necesitan atención`);
    }
}

// Ejecutar las pruebas
testEndpoints().catch(console.error);
