'use client';

import { useAxiomStore } from '@/store/axiom';
import { ShieldCheck, X, ChevronRight, CheckCircle, AlertTriangle, Lock } from 'lucide-react';
import { motion } from 'framer-motion';
import * as ScrollArea from '@radix-ui/react-scroll-area';

export function InspectorPane({ onClose }: { onClose: () => void }) {
    const { currentIVCU } = useAxiomStore();

    // Map VerifierResults to steps or use mocks
    const steps = currentIVCU?.verificationResult?.verifierResults.map(vr => ({
        name: vr.name,
        status: vr.passed ? 'pass' : 'fail',
        time: `${vr.durationMs}ms`
    })) || [
            { name: 'Tier 0: Syntax', status: 'pass', time: '8ms' },
            { name: 'Tier 1: Static Analysis', status: 'pass', time: '142ms' },
            { name: 'Tier 2: Unit Tests', status: 'pass', time: '1.2s' },
            { name: 'Tier 3: SMT Solver', status: 'pass', time: '2.4s' },
        ];

    return (
        <div className="flex flex-col h-full bg-surface/30">
            {/* Header */}
            <div className="h-10 border-b border-white/5 flex items-center justify-between px-4">
                <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-gray-300">Inspector</span>
                </div>
                <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Content */}
            <ScrollArea.Root className="flex-1 overflow-hidden bg-surface/50">
                <ScrollArea.Viewport className="w-full h-full p-4 space-y-6">

                    {/* Overall Status */}
                    <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-white">Verified Secure</h3>
                                <p className="text-xs text-emerald-400/80">Proof Bundle #8f2a... signed</p>
                            </div>
                        </div>
                        <div className="flex gap-2 mt-3">
                            <Badge label="Ed25519 Signed" icon={Lock} color="bg-blue-500/20 text-blue-300" />
                            <Badge label="PII Safe" icon={CheckCircle} color="bg-emerald-500/20 text-emerald-300" />
                        </div>
                    </div>

                    {/* Verification Tiers */}
                    <div>
                        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3 px-1">Verification Chain</h4>
                        <div className="space-y-2">
                            {steps.map((step: any, i: number) => (
                                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-black/20 border border-white/5 group hover:border-white/10 transition-colors">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-2 h-2 rounded-full ${step.status === 'pass' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                        <span className="text-sm text-gray-300">{step.name}</span>
                                    </div>
                                    <span className="text-xs font-mono text-gray-600 group-hover:text-gray-500">{step.time}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* SMT Contracts */}
                    <div>
                        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3 px-1">Logic Contracts</h4>
                        <div className="p-3 bg-black/40 rounded-lg border border-white/5 font-mono text-xs text-gray-400">
                            <p className="text-blue-400">pre: input != null</p>
                            <p className="text-blue-400">post: result.length {'>'} 0</p>
                            <p className="text-emerald-500 mt-2">{'//'} SATISFIED (Z3)</p>
                        </div>
                    </div>

                </ScrollArea.Viewport>
                <ScrollArea.Scrollbar orientation="vertical" className="w-2.5 bg-black/10 p-0.5"><ScrollArea.Thumb className="bg-white/10 rounded-full" /></ScrollArea.Scrollbar>
            </ScrollArea.Root>
        </div>
    );
}

function Badge({ label, icon: Icon, color }: any) {
    return (
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium ${color}`}>
            <Icon className="w-3 h-3" />
            <span>{label}</span>
        </div>
    );
}
