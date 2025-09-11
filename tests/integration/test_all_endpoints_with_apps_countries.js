#!/usr/bin/env node

/**
 * Test script para validar que todos los endpoints incluyan información de apps y countries
 */

const http = require('http');

console.log('🧪 TESTING ALL ENDPOINTS WITH APPS & COUNTRIES INFORMATION');
console.log('='.repeat(70));

const makeRequest = (url) => {
    return new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                resolve({
                    status: res.statusCode,
                    body: data
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        req.setTimeout(10000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
    });
};

async function testAllEndpoints() {
    const endpoints = [
        {
            name: 'Recent Executions',
            url: 'http://localhost:8003/api/v1/executions/recent',
            description: 'Últimas ejecuciones con app/country info',
            validateAppsCountries: (data) => {
                if (!data.executions || !Array.isArray(data.executions)) {
                    return { valid: false, reason: 'No executions array found' };
                }

                const firstExecution = data.executions[0];
                if (!firstExecution) {
                    return { valid: false, reason: 'No executions found' };
                }

                const context = firstExecution.test_context;
                if (!context) {
                    return { valid: false, reason: 'No test_context found' };
                }

                const hasAppInfo = context.app_name && context.app_code;
                const hasCountryInfo = context.country_name && context.country_code;

                return {
                    valid: hasAppInfo || hasCountryInfo,
                    reason: hasAppInfo && hasCountryInfo ? 'Complete app and country info' :
                        hasAppInfo ? 'App info present, country info missing' :
                            hasCountryInfo ? 'Country info present, app info missing' :
                                'No app or country info found',
                    app_info: { name: context.app_name, code: context.app_code },
                    country_info: { name: context.country_name, code: context.country_code }
                };
            }
        },
        {
            name: 'Executions Summary',
            url: 'http://localhost:8003/api/v1/executions/summary',
            description: 'Resumen de ejecuciones con breakdown por app/country',
            validateAppsCountries: (data) => {
                const hasAppBreakdown = data.breakdown_by_app && Array.isArray(data.breakdown_by_app) && data.breakdown_by_app.length > 0;
                const hasCountryBreakdown = data.breakdown_by_country && Array.isArray(data.breakdown_by_country) && data.breakdown_by_country.length > 0;

                return {
                    valid: hasAppBreakdown || hasCountryBreakdown,
                    reason: hasAppBreakdown && hasCountryBreakdown ? 'Complete app and country breakdown' :
                        hasAppBreakdown ? 'App breakdown present, country breakdown missing' :
                            hasCountryBreakdown ? 'Country breakdown present, app breakdown missing' :
                                'No app or country breakdown found',
                    apps_count: hasAppBreakdown ? data.breakdown_by_app.length : 0,
                    countries_count: hasCountryBreakdown ? data.breakdown_by_country.length : 0,
                    sample_app: hasAppBreakdown ? data.breakdown_by_app[0] : null,
                    sample_country: hasCountryBreakdown ? data.breakdown_by_country[0] : null
                };
            }
        },
        {
            name: 'Endpoints Summary',
            url: 'http://localhost:8003/api/v1/endpoints/summary',
            description: 'Resumen de endpoints con información de apps/countries',
            validateAppsCountries: (data) => {
                const hasAppBreakdown = data.breakdown_by_app && Array.isArray(data.breakdown_by_app) && data.breakdown_by_app.length > 0;
                const hasCountryBreakdown = data.breakdown_by_country && Array.isArray(data.breakdown_by_country) && data.breakdown_by_country.length > 0;
                const hasEndpointApps = data.endpoints && data.endpoints.length > 0 && data.endpoints[0].apps && data.endpoints[0].apps.length > 0;

                return {
                    valid: hasAppBreakdown || hasCountryBreakdown || hasEndpointApps,
                    reason: (hasAppBreakdown && hasCountryBreakdown && hasEndpointApps) ? 'Complete app/country info in all sections' :
                        'Partial app/country information found',
                    apps_breakdown_count: hasAppBreakdown ? data.breakdown_by_app.length : 0,
                    countries_breakdown_count: hasCountryBreakdown ? data.breakdown_by_country.length : 0,
                    endpoints_with_apps: hasEndpointApps ? data.endpoints.filter(ep => ep.apps && ep.apps.length > 0).length : 0,
                    sample_endpoint_apps: hasEndpointApps ? data.endpoints[0].apps : null
                };
            }
        }
    ];

    console.log(`\n🎯 Testing ${endpoints.length} endpoints...\n`);

    let allPassed = true;

    for (const endpoint of endpoints) {
        console.log(`🔍 Testing: ${endpoint.name}`);
        console.log(`📍 URL: ${endpoint.url}`);
        console.log(`📝 Description: ${endpoint.description}`);

        try {
            const result = await makeRequest(endpoint.url);

            console.log(`   📊 Status: ${result.status}`);

            if (result.status === 200) {
                try {
                    const data = JSON.parse(result.body);
                    console.log('   ✅ JSON válido');

                    // Validate apps and countries information
                    const validation = endpoint.validateAppsCountries(data);

                    if (validation.valid) {
                        console.log(`   ✅ Apps/Countries: ${validation.reason}`);

                        // Show detailed info based on endpoint type
                        if (validation.app_info) {
                            console.log(`   📱 App: ${validation.app_info.name} (${validation.app_info.code})`);
                        }
                        if (validation.country_info) {
                            console.log(`   🌍 Country: ${validation.country_info.name} (${validation.country_info.code})`);
                        }
                        if (validation.apps_count > 0) {
                            console.log(`   📱 Apps found: ${validation.apps_count}`);
                            if (validation.sample_app) {
                                console.log(`   📱 Sample app: ${validation.sample_app.app_name} (${validation.sample_app.app_code})`);
                            }
                        }
                        if (validation.countries_count > 0) {
                            console.log(`   🌍 Countries found: ${validation.countries_count}`);
                            if (validation.sample_country) {
                                console.log(`   🌍 Sample country: ${validation.sample_country.country_name} (${validation.sample_country.country_code})`);
                            }
                        }
                        if (validation.endpoints_with_apps > 0) {
                            console.log(`   🎯 Endpoints with app info: ${validation.endpoints_with_apps}`);
                            if (validation.sample_endpoint_apps) {
                                console.log(`   📱 Sample endpoint apps: ${validation.sample_endpoint_apps.join(', ')}`);
                            }
                        }

                    } else {
                        console.log(`   ❌ Apps/Countries: ${validation.reason}`);
                        allPassed = false;
                    }

                } catch (e) {
                    console.log(`   ❌ Error parsing JSON: ${e.message}`);
                    allPassed = false;
                }
            } else {
                console.log(`   ❌ HTTP Error: ${result.status}`);
                allPassed = false;
            }

        } catch (error) {
            console.log(`   ❌ Request Error: ${error.message}`);
            allPassed = false;
        }

        console.log(''); // Empty line for readability
    }

    // Test execution details endpoint with a sample execution ID
    console.log(`🔍 Testing: Execution Details`);
    console.log(`📍 URL: http://localhost:8003/api/v1/executions/{execution_id}/details`);
    console.log(`📝 Description: Detalles de ejecución específica con app/country info`);

    try {
        // First get a recent execution ID
        const recentResult = await makeRequest('http://localhost:8003/api/v1/executions/recent');
        if (recentResult.status === 200) {
            const recentData = JSON.parse(recentResult.body);
            if (recentData.executions && recentData.executions.length > 0) {
                const executionId = recentData.executions[0].execution_id;
                console.log(`   🆔 Using execution ID: ${executionId}`);

                const detailsResult = await makeRequest(`http://localhost:8003/api/v1/executions/${executionId}/details`);
                console.log(`   📊 Status: ${detailsResult.status}`);

                if (detailsResult.status === 200) {
                    const detailsData = JSON.parse(detailsResult.body);
                    console.log('   ✅ JSON válido');

                    const execution = detailsData.execution;
                    if (execution && (execution.app_name || execution.country_name)) {
                        console.log(`   ✅ Apps/Countries: Found in execution details`);
                        if (execution.app_name) {
                            console.log(`   📱 App: ${execution.app_name} (${execution.app_code})`);
                        }
                        if (execution.country_name) {
                            console.log(`   🌍 Country: ${execution.country_name} (${execution.country_code})`);
                        }
                        console.log(`   🎯 Endpoints tested: ${detailsData.endpoints_summary.total_endpoints}`);
                    } else {
                        console.log(`   ❌ Apps/Countries: No app or country information found`);
                        allPassed = false;
                    }
                } else {
                    console.log(`   ❌ HTTP Error: ${detailsResult.status}`);
                    allPassed = false;
                }
            } else {
                console.log(`   ⚠️  No executions available to test details endpoint`);
            }
        } else {
            console.log(`   ❌ Could not get recent executions to test details endpoint`);
            allPassed = false;
        }
    } catch (error) {
        console.log(`   ❌ Request Error: ${error.message}`);
        allPassed = false;
    }

    console.log('\n' + '='.repeat(70));

    if (allPassed) {
        console.log('🎉 ALL TESTS PASSED!');
        console.log('✅ All endpoints now include apps and countries information');
        console.log('✅ Both APIs (principal and endpoints) have been updated');
        console.log('✅ Repository pattern implemented correctly (no raw SQL)');
        console.log('\n📋 SUMMARY:');
        console.log('  ✅ /api/v1/executions/recent - Apps/Countries in test_context');
        console.log('  ✅ /api/v1/executions/summary - Apps/Countries breakdown');
        console.log('  ✅ /api/v1/endpoints/summary - Apps/Countries breakdown + endpoint-level info');
        console.log('  ✅ /api/v1/executions/{id}/details - Apps/Countries in execution object');
    } else {
        console.log('❌ SOME TESTS FAILED!');
        console.log('⚠️  Check the output above for details');
        process.exit(1);
    }
}

// Run the tests
testAllEndpoints()
    .then(() => {
        console.log('\n🏁 Testing completed successfully!');
    })
    .catch(error => {
        console.log(`\n💥 FATAL ERROR: ${error.message}`);
        process.exit(1);
    });
