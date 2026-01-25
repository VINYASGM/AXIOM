'use client';

import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Target, Zap, RefreshCw } from 'lucide-react';

const AI_SERVICE_URL = 'http://localhost:8002';

interface BanditArm {
    id: string;
    temperature: number;
    candidate_count: number;
    mean: number;
    total_trials: number;
}

interface GenerationStats {
    total_generations: number;
    successful: number;
    success_rate: number;
    bandit_arms: BanditArm[];
    overall_stats: {
        total_generations: number;
        successful_verifications: number;
        avg_confidence: number;
    };
}

export function GenerationStatsPanel() {
    const [stats, setStats] = useState<GenerationStats | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${AI_SERVICE_URL}/stats/generation`);
            const data = await res.json();
            setStats(data);
        } catch (err) {
            console.error('Failed to fetch stats', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 60000); // Refresh every minute
        return () => clearInterval(interval);
    }, []);

    if (loading && !stats) {
        return (
            <div className="glass rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="w-5 h-5 text-axiom-400" />
                    <h3 className="font-medium text-white">Generation Stats</h3>
                </div>
                <div className="flex justify-center py-8">
                    <RefreshCw className="w-6 h-6 text-gray-500 animate-spin" />
                </div>
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-xl p-5"
        >
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-axiom-400" />
                    <h3 className="font-medium text-white">Generation Stats</h3>
                </div>
                <button
                    onClick={fetchStats}
                    className="p-1.5 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {stats && (
                <div className="space-y-4">
                    {/* Summary Stats */}
                    <div className="grid grid-cols-3 gap-3">
                        <div className="text-center p-3 bg-white/5 rounded-lg">
                            <div className="text-2xl font-bold text-white">
                                {stats.total_generations}
                            </div>
                            <div className="text-xs text-gray-500">Total</div>
                        </div>
                        <div className="text-center p-3 bg-white/5 rounded-lg">
                            <div className="text-2xl font-bold text-green-400">
                                {stats.successful}
                            </div>
                            <div className="text-xs text-gray-500">Verified</div>
                        </div>
                        <div className="text-center p-3 bg-white/5 rounded-lg">
                            <div className="text-2xl font-bold text-axiom-400">
                                {Math.round(stats.success_rate * 100)}%
                            </div>
                            <div className="text-xs text-gray-500">Success</div>
                        </div>
                    </div>

                    {/* Bandit Arms */}
                    {stats.bandit_arms && stats.bandit_arms.length > 0 && (
                        <div className="pt-3 border-t border-white/5">
                            <div className="flex items-center gap-2 mb-3">
                                <Target className="w-4 h-4 text-purple-400" />
                                <span className="text-sm text-gray-400">Thompson Sampling Arms</span>
                            </div>
                            <div className="space-y-2">
                                {stats.bandit_arms.slice(0, 4).map(arm => (
                                    <div key={arm.id} className="flex items-center gap-3">
                                        <div className="flex-1">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-xs text-gray-300 font-medium">
                                                    {arm.id}
                                                </span>
                                                <span className="text-xs text-gray-500">
                                                    {arm.total_trials} trials
                                                </span>
                                            </div>
                                            <div className="w-full bg-white/5 rounded-full h-1.5">
                                                <div
                                                    className="h-1.5 rounded-full bg-gradient-to-r from-axiom-500 to-purple-500 transition-all"
                                                    style={{ width: `${arm.mean * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                        <span className="text-xs text-axiom-400 w-10 text-right">
                                            {Math.round(arm.mean * 100)}%
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Avg Confidence */}
                    {stats.overall_stats && (
                        <div className="flex items-center justify-between pt-3 border-t border-white/5 text-sm">
                            <div className="flex items-center gap-2 text-gray-400">
                                <TrendingUp className="w-4 h-4" />
                                Avg Confidence
                            </div>
                            <span className="text-axiom-400 font-medium">
                                {Math.round(stats.overall_stats.avg_confidence * 100)}%
                            </span>
                        </div>
                    )}
                </div>
            )}

            {!stats && (
                <div className="text-center py-6 text-gray-500">
                    <Zap className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No generation data yet</p>
                </div>
            )}
        </motion.div>
    );
}
