// React Frontend - Examples for consuming QA Intelligence Metrics API
// Ejemplos de hooks y componentes para integrar con el API de métricas

// 1. Custom Hook para métricas de ejecuciones
import { useEffect, useState } from 'react';

// Hook para métricas de ejecuciones
export const useExecutionMetrics = (refreshInterval = 30000) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await fetch('http://localhost:8003/api/v1/executions/summary');
                if (!response.ok) throw new Error('Failed to fetch execution metrics');
                const result = await response.json();
                setData(result);
                setError(null);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, refreshInterval);
        return () => clearInterval(interval);
    }, [refreshInterval]);

    return { data, loading, error };
};

// Hook para métricas de endpoints
export const useEndpointMetrics = (refreshInterval = 30000) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await fetch('http://localhost:8003/api/v1/endpoints/summary');
                if (!response.ok) throw new Error('Failed to fetch endpoint metrics');
                const result = await response.json();
                setData(result);
                setError(null);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, refreshInterval);
        return () => clearInterval(interval);
    }, [refreshInterval]);

    return { data, loading, error };
};

// Hook para problemas detectados
export const useEndpointProblems = (refreshInterval = 60000) => {
    const [problems, setProblems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchProblems = async () => {
            try {
                setLoading(true);
                const response = await fetch('http://localhost:8003/api/v1/endpoints/problems');
                if (!response.ok) throw new Error('Failed to fetch problems');
                const result = await response.json();
                setProblems(result.problems || []);
                setError(null);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchProblems();
        const interval = setInterval(fetchProblems, refreshInterval);
        return () => clearInterval(interval);
    }, [refreshInterval]);

    return { problems, loading, error };
};

// 2. Componente Dashboard Principal
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

export const QADashboard = () => {
    const { data: executions, loading: executionsLoading } = useExecutionMetrics();
    const { data: endpoints, loading: endpointsLoading } = useEndpointMetrics();
    const { problems, loading: problemsLoading } = useEndpointProblems();

    if (executionsLoading || endpointsLoading) {
        return <div className="flex justify-center p-8">Loading metrics...</div>;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
            {/* Execution Summary */}
            <Card>
                <CardHeader>
                    <h3 className="text-lg font-semibold">🚀 Execution Summary</h3>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <span>Completed:</span>
                            <span className="font-bold text-green-600">
                                {executions?.total_completed || 0}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span>Failed:</span>
                            <span className="font-bold text-red-600">
                                {executions?.total_failed || 0}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span>Success Rate:</span>
                            <span className="font-bold">
                                {executions ?
                                    `${((executions.total_completed / (executions.total_completed + executions.total_failed)) * 100).toFixed(1)}%`
                                    : 'N/A'
                                }
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Problems Alert */}
            <Card>
                <CardHeader>
                    <h3 className="text-lg font-semibold">🚨 Active Problems</h3>
                </CardHeader>
                <CardContent>
                    {problemsLoading ? (
                        <div>Loading problems...</div>
                    ) : problems.length > 0 ? (
                        <div className="space-y-2">
                            {problems.slice(0, 3).map((problem, index) => (
                                <Alert key={index} className={problem.severity === 'critical' ? 'border-red-500' : 'border-yellow-500'}>
                                    <AlertDescription>
                                        <strong>{problem.endpoint}</strong>: {problem.message}
                                    </AlertDescription>
                                </Alert>
                            ))}
                            {problems.length > 3 && (
                                <div className="text-sm text-gray-500">
                                    +{problems.length - 3} more problems
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="text-green-600">✅ No problems detected</div>
                    )}
                </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card>
                <CardHeader>
                    <h3 className="text-lg font-semibold">📊 Quick Stats</h3>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <span>Endpoints Monitored:</span>
                            <span className="font-bold">
                                {endpoints?.endpoints?.total_requests?.length || 0}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span>Critical Issues:</span>
                            <span className="font-bold text-red-600">
                                {problems.filter(p => p.severity === 'critical').length}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span>Warnings:</span>
                            <span className="font-bold text-yellow-600">
                                {problems.filter(p => p.severity === 'warning').length}
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

// 3. Componente de métricas detalladas por endpoint
export const EndpointDetail = ({ endpointName, method }) => {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState(1); // hours

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                setLoading(true);
                const url = new URL(`http://localhost:8003/api/v1/endpoints/${encodeURIComponent(endpointName)}/metrics`);
                if (method) url.searchParams.set('method', method);
                url.searchParams.set('hours', timeRange.toString());

                const response = await fetch(url);
                if (!response.ok) throw new Error('Failed to fetch endpoint metrics');
                const result = await response.json();
                setMetrics(result);
            } catch (err) {
                console.error('Error fetching endpoint metrics:', err);
            } finally {
                setLoading(false);
            }
        };

        if (endpointName) {
            fetchMetrics();
        }
    }, [endpointName, method, timeRange]);

    if (loading) return <div>Loading endpoint details...</div>;
    if (!metrics) return <div>No data available</div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold">
                    {method} {endpointName}
                </h2>
                <select
                    value={timeRange}
                    onChange={(e) => setTimeRange(Number(e.target.value))}
                    className="border rounded px-3 py-1"
                >
                    <option value={1}>Last 1 hour</option>
                    <option value={6}>Last 6 hours</option>
                    <option value={24}>Last 24 hours</option>
                </select>
            </div>

            {/* Charts would go here - using your preferred charting library */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardHeader>
                        <h3>Response Time (P95)</h3>
                    </CardHeader>
                    <CardContent>
                        {/* Chart component for response time */}
                        <div>Response time chart placeholder</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <h3>Request Rate</h3>
                    </CardHeader>
                    <CardContent>
                        {/* Chart component for request rate */}
                        <div>Request rate chart placeholder</div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

// 4. Service para API calls
export class MetricsService {
    constructor(baseUrl = 'http://localhost:8003') {
        this.baseUrl = baseUrl;
    }

    async getExecutionSummary() {
        const response = await fetch(`${this.baseUrl}/api/v1/executions/summary`);
        if (!response.ok) throw new Error('Failed to fetch execution summary');
        return response.json();
    }

    async getEndpointSummary() {
        const response = await fetch(`${this.baseUrl}/api/v1/endpoints/summary`);
        if (!response.ok) throw new Error('Failed to fetch endpoint summary');
        return response.json();
    }

    async getEndpointMetrics(endpointName, options = {}) {
        const url = new URL(`${this.baseUrl}/api/v1/endpoints/${encodeURIComponent(endpointName)}/metrics`);

        if (options.method) url.searchParams.set('method', options.method);
        if (options.hours) url.searchParams.set('hours', options.hours.toString());

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch endpoint metrics');
        return response.json();
    }

    async getProblems() {
        const response = await fetch(`${this.baseUrl}/api/v1/endpoints/problems`);
        if (!response.ok) throw new Error('Failed to fetch problems');
        return response.json();
    }

    async executePromQLQuery(query) {
        const url = new URL(`${this.baseUrl}/api/v1/metrics/raw`);
        url.searchParams.set('query', query);

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to execute query');
        return response.json();
    }
}

// 5. Configuración de tipos TypeScript (opcional)
export interface ExecutionSummary {
    total_completed: number;
    total_failed: number;
    current_states: Record<string, number>;
    timestamp: string;
}

export interface EndpointProblem {
    type: 'high_error_rate' | 'slow_response';
    severity: 'critical' | 'warning';
    endpoint: string;
    method: string;
    value: number;
    threshold: number;
    message: string;
}

export interface EndpointMetrics {
    endpoint: string;
    method?: string;
    time_range: {
        start: string;
        end: string;
    };
    metrics: {
        requests: Array<{ labels: Record<string, string>; values: Array<{ timestamp: number; value: number }> }>;
        response_time_p95: Array<{ labels: Record<string, string>; values: Array<{ timestamp: number; value: number }> }>;
        error_rate: Array<{ labels: Record<string, string>; values: Array<{ timestamp: number; value: number }> }>;
        rps: Array<{ labels: Record<string, string>; values: Array<{ timestamp: number; value: number }> }>;
    };
    timestamp: string;
}
