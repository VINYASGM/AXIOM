'use client';

import { Activity, Cpu, Server, ShieldCheck, Zap } from 'lucide-react';
import { useAxiomStore } from '@/store/axiom';
import { motion } from 'framer-motion';

export function IntelligenceDashboard() {
    const { isGenerating, costEstimate, currentIVCU } = useAxiomStore();

    // Mock metrics for simulation
    const metrics = {
        activeContexts: isGenerating ? 1 : 0,
        memoryUsage: '1.2 GB',
        generationSpeed: '45 t/s',
        uptime: '99.9%',
    };

    return (
        <div className="glass rounded-2xl p-6 h-full">
            <div className="flex items-center gap-2 mb-6">
                <Activity className="w-5 h-5 text-axiom-400" />
                <h2 className="text-lg font-semibold text-white">System Intelligence</h2>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {/* Metric Cards */}
                <MetricCard
                    icon={Cpu}
                    label="Active Contexts"
                    value={metrics.activeContexts.toString()}
                    status={isGenerating ? 'active' : 'idle'}
                />
                <MetricCard
                    icon={Zap}
                    label="Gen Speed"
                    value={metrics.generationSpeed}
                />
                <MetricCard
                    icon={Server}
                    label="Memory"
                    value={metrics.memoryUsage}
                />
                <MetricCard
                    icon={ShieldCheck}
                    label="Verifier Health"
                    value="Optimal"
                    color="text-green-400"
                />
            </div>

            {/* Recent Activity / Cost */}
            <div className="mt-6 pt-6 border-t border-white/5">
                <h3 className="text-sm font-medium text-gray-400 mb-3">Resource & Cost</h3>

                <div className="space-y-3">
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-500">Session Spend</span>
                        <span className="text-white font-mono">
                            ${(currentIVCU?.costUsd || 0).toFixed(4)}
                        </span>
                    </div>

                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-500">Est. Next Generation</span>
                        <span className="text-axiom-300 font-mono">
                            ${costEstimate ? costEstimate.estimatedCostUsd.toFixed(4) : '0.0000'}
                        </span>
                    </div>

                    <div className="mt-2 w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                        <motion.div
                            className="h-full bg-axiom-500"
                            initial={{ width: 0 }}
                            animate={{ width: isGenerating ? '60%' : '10%' }}
                            transition={{ duration: 0.5 }}
                        />
                    </div>
                    <div className="text-xs text-right text-gray-600 mt-1">Daily Cap: $5.00</div>
                </div>
            </div>
        </div>
    );
}

function MetricCard({
    icon: Icon,
    label,
    value,
    status,
    color = "text-white"
}: {
    icon: any,
    label: string,
    value: string,
    status?: 'active' | 'idle',
    color?: string
}) {
    return (
        <div className="bg-black/20 rounded-xl p-3 border border-white/5">
            <div className="flex items-center gap-2 mb-2 text-gray-500 text-xs">
                <Icon className={`w-3 h-3 ${status === 'active' ? 'text-axiom-400 animate-pulse' : ''}`} />
                {label}
            </div>
            <div className={`text-lg font-mono font-medium ${color}`}>
                {value}
            </div>
        </div>
    );
}
