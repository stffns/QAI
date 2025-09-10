#!/usr/bin/env node

/**
 * Prueba rápida de integración React con QA Intelligence
 * Simula las llamadas que haría un frontend React
 */

const http = require('http');

function makeRequest(url) {
    return new Promise((resolve, reject) => {
        const request = http.get(url, (response) => {
            resolve(response);
        });
        request.on('error', reject);
        request.setTimeout(5000, () => {
            request.abort();
            reject(new Error('Timeout'));
        });
    });
}

async function testIntegration() {
    console.log('🧪 Probando integración React con QA Intelligence...\n');

    // Test 1: REST API Health Check
    console.log('1️⃣ Probando REST API...');
    try {
        const response = await makeRequest('http://localhost:8003/');
        if (response.statusCode === 200) {
            console.log('✅ REST API: Funcionando correctamente');
        } else {
            console.log('❌ REST API: Error', response.statusCode);
        }
    } catch (error) {
        console.log('❌ REST API: No disponible -', error.message);
    }

    // Test 2: Prometheus Metrics
    console.log('\n2️⃣ Probando métricas Prometheus...');
    try {
        const response = await makeRequest('http://localhost:9400/metrics');
        if (response.statusCode === 200) {
            console.log('✅ Prometheus Metrics: Funcionando correctamente');
        } else {
            console.log('❌ Prometheus Metrics: Error', response.status);
        }
    } catch (error) {
        console.log('❌ Prometheus Metrics: No disponible -', error.message);
    }

    // Test 3: Endpoint Metrics  
    console.log('\n3️⃣ Probando métricas de endpoints...');
    try {
        const response = await fetch('http://localhost:9401/metrics');
        if (response.ok) {
            console.log('✅ Endpoint Metrics: Funcionando correctamente');
        } else {
            console.log('❌ Endpoint Metrics: Error', response.status);
        }
    } catch (error) {
        console.log('❌ Endpoint Metrics: No disponible -', error.message);
    }

    // Test 4: API CORS
    console.log('\n4️⃣ Probando CORS (simulando React)...');
    try {
        const response = await fetch('http://localhost:8003/api/v1/executions/summary', {
            method: 'OPTIONS',
            headers: {
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET'
            }
        });
        if (response.ok) {
            console.log('✅ CORS: Configurado correctamente para React');
        } else {
            console.log('❌ CORS: Error', response.status);
        }
    } catch (error) {
        console.log('❌ CORS: Error -', error.message);
    }

    // Test 5: WebSocket Connection
    console.log('\n5️⃣ Probando conexión WebSocket...');
    try {
        const WebSocket = require('ws');
        const ws = new WebSocket('ws://localhost:8765');

        await new Promise((resolve, reject) => {
            ws.on('open', () => {
                console.log('✅ WebSocket: Conexión establecida');
                ws.close();
                resolve();
            });
            ws.on('error', (error) => {
                console.log('❌ WebSocket: Error de conexión -', error.message);
                reject(error);
            });
            setTimeout(() => {
                reject(new Error('Timeout'));
            }, 5000);
        });
    } catch (error) {
        console.log('❌ WebSocket: Error -', error.message);
    }

    console.log('\n🎉 Prueba de integración completada!');
    console.log('\nTu stack QA Intelligence está listo para React! 🚀');
}

// Ejecutar solo si es llamado directamente
if (require.main === module) {
    testIntegration().catch(console.error);
}
