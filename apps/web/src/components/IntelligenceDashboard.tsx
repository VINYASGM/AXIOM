'use client';

import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import {
    Database,
    Cpu,
    Shield,
    Activity,
    Zap,
    RefreshCw,
    Trash2,
    TrendingUp,
    AlertTriangle,
    CheckCircle2
} from 'lucide-react';

// API base URL for the AI service
const AI_SERVICE_URL = 'http://localhost:8002';

interface CacheStats {
    size: number;
    max_size: number;
    hits: number;
    misses: number;
    semantic_hits: number;
    hit_rate: number;
    total_requests: number;
}

interface RouterMetrics {
    requests: Record<string, number>;
    errors: Record<string, number>;
    avg_latency_ms: Record<string, number>;
}

interface PolicyRule {
    id: string;
    name: string;
    phase: string;
    severity: string;
    enabled: boolean;
}

export function IntelligenceDashboard() {
    const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
    const [routerMetrics, setRouterMetrics] = useState<RouterMetrics | null>(null);
    const [providers, setProviders] = useState<string[]>([]);
    const [policyRules, setPolicyRules] = useState<PolicyRule[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);

        try {
            const [cacheRes, routerRes, providersRes, policyRes] = await Promise.all([
                fetch(`${AI_SERVICE_URL}/cache/stats`).then(r => r.json()),
                fetch(`${AI_SERVICE_URL}/router/metrics`).then(r => r.json()),
                fetch(`${AI_SERVICE_URL}/router/providers`).then(r => r.json()),
                fetch(`${AI_SERVICE_URL}/policy/rules`).then(r => r.json())
            ]);

            setCacheStats(cacheRes);
            setRouterMetrics(routerRes);
            setProviders(providersRes.providers || []);
            setPolicyRules(policyRes.rules || []);
        } catch (err) {
            setError('Failed to fetch intelligence layer stats');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const clearCache = async () => {
        try {
            await fetch(`${AI_SERVICE_URL}/cache/clear`, { method: 'DELETE' });
            fetchData();
        } catch (err) {
            console.error('Failed to clear cache', err);
        }
    };

    useEffect(() => {
        fetchData();
        // Auto-refresh every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading && !cacheStats) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="w-8 h-8 text-axiom-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Cpu className="w-6 h-6 text-axiom-400" />
                    <h2 className="text-xl font-semibold text-white">Intelligence Layer</h2>
                </div>
                <button
                    onClick={fetchData}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors text-sm"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
            </div>

            {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Cache Stats */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass rounded-xl p-5"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Database className="w-5 h-5 text-blue-400" />
                            <h3 className="font-medium text-white">Semantic Cache</h3>
                        </div>
                        <button
                            onClick={clearCache}
                            className="p-1.5 rounded hover:bg-white/10 text-gray-500 hover:text-red-400 transition-colors"
                            title="Clear cache"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>

                    {cacheStats && (
                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-400">Entries</span>
                                <span className="text-white">{cacheStats.size} / {cacheStats.max_size}</span>
                            </div>
                            <div className="w-full bg-white/5 rounded-full h-2">
                                <div
                                    className="bg-blue-500 h-2 rounded-full transition-all"
                                    style={{ width: `${(cacheStats.size / cacheStats.max_size) * 100}%` }}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-2 mt-4">
                                <div className="text-center p-2 bg-white/5 rounded-lg">
                                    <div className="text-lg font-semibold text-green-400">
                                        {Math.round(cacheStats.hit_rate * 100)}%
                                    </div>
                                    <div className="text-xs text-gray-500">Hit Rate</div>
                                </div>
                                <div className="text-center p-2 bg-white/5 rounded-lg">
                                    <div className="text-lg font-semibold text-purple-400">
                                        {cacheStats.semantic_hits}
                                    </div>
                                    <div className="text-xs text-gray-500">Semantic Hits</div>
                                </div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-500 pt-2 border-t border-white/5">
                                <span>Hits: {cacheStats.hits}</span>
                                <span>Misses: {cacheStats.misses}</span>
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* Router Stats */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass rounded-xl p-5"
                >
                    <div className="flex items-center gap-2 mb-4">
                        <Zap className="w-5 h-5 text-amber-400" />
                        <h3 className="font-medium text-white">LLM Router</h3>
                    </div>

                    <div className="space-y-3">
                        <div className="text-sm text-gray-400 mb-2">
                            Providers: {providers.length}
                        </div>

                        {providers.map(provider => (
                            <div key={provider} className="flex items-center justify-between p-2 bg-white/5 rounded-lg">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-green-400" />
                                    <span className="text-sm font-medium text-white capitalize">{provider}</span>
                                </div>
                                <div className="text-xs text-gray-400">
                                    {routerMetrics?.requests[provider] || 0} reqs
                                </div>
                            </div>
                        ))}

                        {routerMetrics && Object.keys(routerMetrics.avg_latency_ms).length > 0 && (
                            <div className="pt-2 border-t border-white/5">
                                <div className="text-xs text-gray-500 mb-1">Avg Latency</div>
                                {Object.entries(routerMetrics.avg_latency_ms).map(([provider, latency]) => (
                                    <div key={provider} className="flex justify-between text-xs">
                                        <span className="text-gray-400 capitalize">{provider}</span>
                                        <span className="text-white">{latency}ms</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* Policy Stats */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass rounded-xl p-5"
                >
                    <div className="flex items-center gap-2 mb-4">
                        <Shield className="w-5 h-5 text-green-400" />
                        <h3 className="font-medium text-white">Policy Engine</h3>
                    </div>

                    <div className="space-y-2">
                        <div className="text-sm text-gray-400 mb-3">
                            {policyRules.length} rules active
                        </div>

                        {policyRules.slice(0, 4).map(rule => (
                            <div key={rule.id} className="flex items-center gap-2 text-sm">
                                {rule.severity === 'critical' ? (
                                    <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                                ) : rule.severity === 'error' ? (
                                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                                ) : (
                                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                                )}
                                <span className="text-gray-300 truncate">{rule.name}</span>
                                <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${rule.phase === 'pre_generation'
                                    ? 'bg-purple-500/20 text-purple-400'
                                    : 'bg-cyan-500/20 text-cyan-400'
                                    }`}>
                                    {rule.phase === 'pre_generation' ? 'Pre' : 'Post'}
                                </span>
                            </div>
                        ))}

                        {policyRules.length > 4 && (
                            <div className="text-xs text-gray-500 pt-2">
                                +{policyRules.length - 4} more rules
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>

            {/* Summary Bar */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="flex items-center justify-between p-4 bg-gradient-to-r from-axiom-500/10 to-purple-500/10 rounded-xl border border-axiom-500/20"
            >
                <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-axiom-400" />
                        <span className="text-gray-400">Phase 3 Active</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-green-400" />
                        <span className="text-gray-400">
                            {cacheStats?.total_requests || 0} total requests
                        </span>
                    </div>
                </div>
                <div className="text-xs text-gray-500">
                    Last updated: {new Date().toLocaleTimeString()}
                </div>
            </motion.div>
        </div>
    );
}
