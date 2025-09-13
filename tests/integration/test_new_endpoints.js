const http = require('http');

console.log('🔍 PROBANDO NUEVOS ENDPOINTS DE EJECUCIONES');
console.log('==============================================\n');

// Helper para hacer requests HTTP
function makeRequest(url, method = 'GET') {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const client = http;

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

async function testNewEndpoints() {
    console.log('📋 Probando endpoints nuevos...\n');

    try {
        // 1. Probar el endpoint de ejecución reciente
        console.log('🔍 1. Probando: GET /api/v1/executions/recent');
        const recentResult = await makeRequest('http://localhost:8003/api/v1/executions/recent');

        console.log(`   Status: ${recentResult.status}`);

        if (recentResult.status === 200) {
            try {
                const data = JSON.parse(recentResult.body);
                console.log('   ✅ Respuesta JSON válida');

                if (data.execution) {
                    console.log(`   📊 Execution ID: ${data.execution.execution_id}`);
                    console.log(`   📊 Name: ${data.execution.execution_name}`);
                    console.log(`   📊 Status: ${data.execution.status}`);
                    console.log(`   📊 Success Rate: ${data.summary.success_rate}%`);
                    console.log(`   📊 Endpoints Tested: ${data.summary.endpoints_tested}`);

                    // 2. Si encontramos una ejecución, probar los detalles
                    if (data.execution.execution_id) {
                        console.log('\n🔍 2. Probando: GET /api/v1/executions/{execution_id}/details');
                        const detailsUrl = `http://localhost:8003/api/v1/executions/${data.execution.execution_id}/details`;
                        const detailsResult = await makeRequest(detailsUrl);

                        console.log(`   Status: ${detailsResult.status}`);

                        if (detailsResult.status === 200) {
                            try {
                                const detailsData = JSON.parse(detailsResult.body);
                                console.log('   ✅ Respuesta JSON válida');
                                console.log(`   📊 Execution: ${detailsData.execution.execution_name}`);
                                console.log(`   📊 Total Endpoints: ${detailsData.endpoints_summary.total_endpoints}`);
                                console.log(`   📊 Total Requests: ${detailsData.endpoints_summary.total_requests_all_endpoints}`);
                                console.log(`   📊 Overall Success Rate: ${detailsData.endpoints_summary.overall_endpoint_success_rate.toFixed(2)}%`);

                                // Mostrar primeros 3 endpoints
                                if (detailsData.endpoints && detailsData.endpoints.length > 0) {
                                    console.log('\n   🎯 Primeros endpoints:');
                                    detailsData.endpoints.slice(0, 3).forEach((endpoint, index) => {
                                        console.log(`      ${index + 1}. ${endpoint.http_method} ${endpoint.endpoint_name}`);
                                        console.log(`         Requests: ${endpoint.requests.total} (${endpoint.requests.success_rate.toFixed(1)}% success)`);
                                        console.log(`         Avg Response: ${endpoint.response_times.avg?.toFixed(1) || 'N/A'}ms`);
                                    });
                                }
                            } catch (e) {
                                console.log(`   ❌ Error parsing JSON: ${e.message}`);
                                console.log(`   📄 Raw response: ${detailsResult.body.substring(0, 200)}...`);
                            }
                        } else {
                            console.log(`   ❌ Error: ${detailsResult.status}`);
                            console.log(`   📄 Body: ${detailsResult.body.substring(0, 200)}`);
                        }
                    }
                } else {
                    console.log('   ⚠️  No execution data found');
                    console.log(`   📄 Response: ${data.message || 'No message'}`);
                }
            } catch (e) {
                console.log(`   ❌ Error parsing JSON: ${e.message}`);
                console.log(`   📄 Raw response: ${recentResult.body.substring(0, 200)}...`);
            }
        } else {
            console.log(`   ❌ Error: ${recentResult.status}`);
            console.log(`   📄 Body: ${recentResult.body.substring(0, 200)}`);
        }

        // 3. Probar Raw Metrics endpoint
        console.log('\n🔍 3. Probando: GET /api/v1/metrics/raw');
        const rawResult = await makeRequest('http://localhost:8003/api/v1/metrics/raw');

        console.log(`   Status: ${rawResult.status}`);

        if (rawResult.status === 200) {
            try {
                const rawData = JSON.parse(rawResult.body);
                console.log('   ✅ Raw metrics disponibles');
                console.log(`   📊 Prometheus métricas: ${Object.keys(rawData.prometheus_metrics || {}).length}`);
                console.log(`   📊 Endpoint métricas: ${Object.keys(rawData.endpoint_metrics || {}).length}`);
            } catch (e) {
                console.log(`   ❌ Error parsing JSON: ${e.message}`);
            }
        } else {
            console.log(`   ❌ Error: ${rawResult.status}`);
        }

    } catch (error) {
        console.log(`❌ Error general: ${error.message}`);
    }

    console.log('\n🎉 Prueba de nuevos endpoints completada!');
}

// Ejecutar las pruebas
testNewEndpoints().catch(console.error);
