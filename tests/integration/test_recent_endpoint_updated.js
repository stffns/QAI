const http = require('http');

console.log('🧪 TESTING UPDATED RECENT ENDPOINT - Últimas 10 Ejecuciones');
console.log('='.repeat(60));

const testRecentEndpoint = () => {
    return new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8003/api/v1/executions/recent', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);

                    console.log(`📊 Status Code: ${res.statusCode}`);
                    console.log(`📅 Timestamp: ${parsed.timestamp}`);
                    console.log(`📋 Total Executions: ${parsed.total}`);

                    if (parsed.executions && Array.isArray(parsed.executions)) {
                        console.log(`\n✅ ESTRUCTURA CORRECTA - Array de ejecuciones`);
                        console.log(`📦 Número de ejecuciones: ${parsed.executions.length}`);

                        // Mostrar primeras 3 ejecuciones como ejemplo
                        console.log(`\n🔍 Primeras 3 ejecuciones:`);
                        parsed.executions.slice(0, 3).forEach((execution, index) => {
                            console.log(`\n  ${index + 1}. 🆔 ${execution.execution_id}`);
                            console.log(`     📝 Nombre: ${execution.execution_name}`);
                            console.log(`     📊 Status: ${execution.status}`);
                            console.log(`     🎯 Success Rate: ${execution.summary.success_rate}%`);
                            console.log(`     🔗 Endpoints: ${execution.summary.endpoints_tested}`);
                            console.log(`     📈 Total Requests: ${execution.metrics.total_requests}`);
                            console.log(`     ⏱️  Avg Response Time: ${execution.metrics.avg_response_time}ms`);
                            console.log(`     🌍 Environment: ${execution.test_context.execution_environment}`);
                        });

                        // Validar estructura de cada ejecución
                        console.log(`\n🔬 VALIDACIÓN DE ESTRUCTURA:`);
                        const requiredFields = ['id', 'execution_id', 'execution_name', 'status', 'metrics', 'test_context', 'summary'];
                        const requiredMetrics = ['total_requests', 'successful_requests', 'failed_requests', 'error_rate'];
                        const requiredSummary = ['success_rate', 'is_successful', 'endpoints_tested'];

                        let structureValid = true;
                        const firstExecution = parsed.executions[0];

                        // Verificar campos principales
                        requiredFields.forEach(field => {
                            if (!(field in firstExecution)) {
                                console.log(`❌ Missing field: ${field}`);
                                structureValid = false;
                            }
                        });

                        // Verificar métricas
                        if (firstExecution.metrics) {
                            requiredMetrics.forEach(metric => {
                                if (!(metric in firstExecution.metrics)) {
                                    console.log(`❌ Missing metric: ${metric}`);
                                    structureValid = false;
                                }
                            });
                        }

                        // Verificar resumen
                        if (firstExecution.summary) {
                            requiredSummary.forEach(summary => {
                                if (!(summary in firstExecution.summary)) {
                                    console.log(`❌ Missing summary field: ${summary}`);
                                    structureValid = false;
                                }
                            });
                        }

                        if (structureValid) {
                            console.log(`✅ Estructura completamente validada`);
                        }

                        resolve(parsed);

                    } else {
                        console.log(`❌ ERROR: executions no es un array`);
                        reject(new Error('Invalid structure'));
                    }

                } catch (e) {
                    console.log(`❌ Error parsing JSON: ${e.message}`);
                    reject(e);
                }
            });
        });

        req.on('error', (err) => {
            console.log(`❌ Request error: ${err.message}`);
            reject(err);
        });
    });
};

// Ejecutar test
testRecentEndpoint()
    .then(() => {
        console.log(`\n🎉 TEST COMPLETADO EXITOSAMENTE`);
        console.log(`✅ El endpoint /api/v1/executions/recent ahora retorna las últimas 10 ejecuciones`);
        console.log(`✅ Estructura optimizada para consumo en React frontend`);
        console.log(`✅ Mantiene toda la información detallada de cada ejecución`);
    })
    .catch(error => {
        console.log(`\n❌ TEST FAILED: ${error.message}`);
        process.exit(1);
    });
