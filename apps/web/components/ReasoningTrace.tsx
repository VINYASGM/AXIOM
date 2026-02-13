
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BrainCircuit, MessageSquareCode, CheckCircle2, AlertTriangle, Terminal, ChevronRight } from 'lucide-react';
import { ApiClient } from '../lib/api';

interface ReasoningTraceProps {
    ivcuId: string;
}

interface TraceStep {
    role: string;
    content: string;
    timestamp?: string; // Optional, if backend provides it
}

const ReasoningTrace: React.FC<ReasoningTraceProps> = ({ ivcuId }) => {
    const [trace, setTrace] = useState<TraceStep[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let mounted = true;

        const fetchTrace = async () => {
            try {
                setLoading(true);
                const data = await ApiClient.getReasoningTrace(ivcuId);
                if (mounted) {
                    if (data && data.trace && Array.isArray(data.trace.history)) {
                        // Adapt based on actual backend response structure from intelligence.go
                        // "history" seems to be the key in the map returned by AI service
                        setTrace(data.trace.history);
                    } else if (data && Array.isArray(data.trace)) {
                        setTrace(data.trace);
                    } else {
                        setTrace([]);
                    }
                }
            } catch (err) {
                if (mounted) setError("Failed to load reasoning trace");
            } finally {
                if (mounted) setLoading(false);
            }
        };

        if (ivcuId) {
            fetchTrace();
        }

        return () => { mounted = false; };
    }, [ivcuId]);

    if (loading) return (
        <div className="flex items-center justify-center p-8 text-slate-500 text-xs tracking-widest uppercase animate-pulse">
            <BrainCircuit size={16} className="mr-3" />
            Syncing Neural Logs...
        </div>
    );

    if (error) return (
        <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-red-400 text-xs flex items-center">
            <AlertTriangle size={14} className="mr-2" />
            {error}
        </div>
    );

    if (trace.length === 0) return (
        <div className="p-8 text-center text-slate-600 text-xs italic">
            No reasoning artifacts found for this generation unit.
        </div>
    );

    return (
        <div className="space-y-4 font-mono text-sm">
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-white/5">
                <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                    <BrainCircuit size={14} className="text-sky-400" />
                    Cognitive Trace
                </h4>
                <span className="text-[9px] text-slate-600 font-bold bg-white/5 px-2 py-0.5 rounded-full">{trace.length} STEPS</span>
            </div>

            <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scroll pr-2">
                {trace.map((step, idx) => (
                    <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        className={`p-4 rounded-xl border ${step.role === 'user'
                                ? 'bg-slate-800/20 border-white/5'
                                : step.role === 'model' // check actual role name from AI service
                                    ? 'bg-sky-900/10 border-sky-500/10'
                                    : 'bg-emerald-900/10 border-emerald-500/10'
                            }`}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className={`text-[10px] font-bold uppercase tracking-wider ${step.role === 'user' ? 'text-slate-400' : 'text-sky-400'
                                }`}>
                                {step.role === 'user' ? 'Input Context' : 'Neural Processing'}
                            </span>
                            <span className="text-[9px] text-slate-600">STEP {idx + 1}</span>
                        </div>
                        <div className={`whitespace-pre-wrap leading-relaxed ${step.role === 'user' ? 'text-slate-400' : 'text-slate-300'
                            }`}>
                            {step.content}
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

export default ReasoningTrace;
