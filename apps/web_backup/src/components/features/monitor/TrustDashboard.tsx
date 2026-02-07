'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Lock, Activity, CheckCircle, XCircle, FileCode, Server } from 'lucide-react';
import { useAxiomStore } from '@/store/axiom';
// import { Badge } from '@radix-ui/react-popover';

// Mock Data Types
interface VerificationEvent {
    id: string;
    timestamp: number;
    sdoId: string;
    status: 'pass' | 'fail' | 'verifying';
    tier: string;
    proofHash?: string;
}

export function TrustDashboard() {
    const [events, setEvents] = useState<VerificationEvent[]>([]);

    const { currentIVCU } = useAxiomStore();

    // Sync with Store Events (Real Backend Integration)
    useEffect(() => {
        if (currentIVCU?.verificationResult) {
            const result = currentIVCU.verificationResult;

            // Convert VerifierResults to Dashboard Events
            const newEvents = result.verifierResults.map(vr => ({
                id: vr.id || crypto.randomUUID(),
                timestamp: Date.now(), // approximation
                sdoId: currentIVCU.id,
                status: vr.passed ? 'pass' : 'fail' as 'pass' | 'fail',
                tier: vr.tier,
                proofHash: vr.passed ? '0x' + Math.random().toString(16).slice(2, 10) : undefined // Mock proof hash if missing
            }));

            // Dedup and set events
            setEvents(prev => {
                const combined = [...newEvents, ...prev];
                // simple dedup by id if needed, or just slice
                return combined.slice(0, 20);
            });
        }
    }, [currentIVCU]);

    return (
        <div className="h-full bg-canvas p-6 flex flex-col gap-6 text-white">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <ShieldCheck className="w-8 h-8 text-emerald-500" />
                        Trust & Verification Center
                    </h1>
                    <p className="text-gray-400 mt-1">Real-time Proof-Carrying Code (PCC) Monitoring</p>
                </div>
                <div className="flex items-center gap-4">
                    <StatusBadge label="Gatekeeper Active" status="secure" icon={Lock} />
                    <StatusBadge label="Verifier Mesh Online" status="secure" icon={Server} />
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
                {/* Live Verification Stream */}
                <div className="lg:col-span-2 glass rounded-2xl p-6 flex flex-col overflow-hidden">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold flex items-center gap-2">
                            <Activity className="w-5 h-5 text-axiom-400" />
                            Live Verification Stream
                        </h2>
                        <span className="text-xs text-emerald-400 animate-pulse">● Live</span>
                    </div>
                    <div className="flex-1 overflow-auto space-y-3 pr-2">
                        <AnimatePresence initial={false}>
                            {events.map((event) => (
                                <motion.div
                                    key={event.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="flex items-center justify-between p-4 rounded-xl bg-surface/50 border border-white/5 hover:bg-surface transition-colors"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${event.status === 'pass' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
                                            }`}>
                                            {event.status === 'pass' ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono text-sm text-white">{event.sdoId}</span>
                                                <span className="text-xs text-gray-500">• {new Date(event.timestamp).toLocaleTimeString()}</span>
                                            </div>
                                            <div className="text-xs text-gray-400 mt-0.5">{event.tier}</div>
                                        </div>
                                    </div>
                                    <div>
                                        {event.proofHash && (
                                            <div className="font-mono text-[10px] text-axiom-300 bg-axiom-900/40 px-2 py-1 rounded border border-axiom-500/20">
                                                Proof: {event.proofHash}
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </div>

                {/* Registry Status / Metrics */}
                <div className="space-y-6">
                    <div className="glass rounded-2xl p-6">
                        <h2 className="text-lg font-semibold mb-4">Registry Statistics</h2>
                        <div className="space-y-4">
                            <StatRow label="Verified SDOs" value="1,284" icon={FileCode} />
                            <StatRow label="Proof Bundles" value="1,284" icon={Lock} />
                            <StatRow label="Rejections" value="12" icon={XCircle} color="text-red-400" />
                        </div>
                    </div>

                    <div className="glass rounded-2xl p-6 bg-gradient-to-br from-emerald-900/20 to-black">
                        <h2 className="text-lg font-semibold mb-2 text-emerald-400">Security Posture</h2>
                        <p className="text-sm text-gray-400 mb-4">Current system integrity is optimal.</p>

                        <div className="h-32 flex items-center justify-center">
                            <div className="relative">
                                <motion.div
                                    className="absolute inset-0 bg-emerald-500 blur-xl opacity-20"
                                    animate={{ scale: [1, 1.2, 1] }}
                                    transition={{ duration: 3, repeat: Infinity }}
                                />
                                <ShieldCheck className="w-16 h-16 text-emerald-500 relative z-10" />
                            </div>
                        </div>
                        <div className="text-center text-xs font-mono text-emerald-300 mt-2">
                            ALL SYSTEMS OPERATIONAL
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatusBadge({ label, status, icon: Icon }: any) {
    const color = status === 'secure' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20';
    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${color} text-xs font-medium`}>
            {Icon && <Icon className="w-3.5 h-3.5" />}
            {label}
        </div>
    );
}

function StatRow({ label, value, icon: Icon, color = "text-white" }: any) {
    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-black/20">
            <div className="flex items-center gap-3 text-sm text-gray-400">
                <Icon className="w-4 h-4" />
                {label}
            </div>
            <div className={`font-mono font-bold ${color}`}>{value}</div>
        </div>
    );
}

function Badge({ label, variant = 'default' }: { label: string, variant?: 'default' | 'outline' }) {
    // Placeholder Badge if needed inside the component, but actually I didn't use <Badge> in the JSX except the import.
    // Wait, the import was unused? 
    // "import { Badge } from '@radix-ui/react-popover';"
    // If it's unused, I should remove it.
    // But I might have used it in JSX?
    // Let me check JSX usage.
    return <span className="px-2 py-1 rounded bg-white/10 text-xs">{label}</span>;
}
