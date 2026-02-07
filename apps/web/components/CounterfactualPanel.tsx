import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    GitFork,
    ArrowRight,
    RefreshCw,
    Check,
    X,
    Split,
    Zap
} from 'lucide-react';
import { IVCU } from '../types';
import Button from './Button';

interface Props {
    baseIvcu: IVCU;
    onClose: () => void;
    onApply: (newIvcu: IVCU) => void;
}

const CounterfactualPanel: React.FC<Props> = ({ baseIvcu, onClose, onApply }) => {
    const [prompt, setPrompt] = useState("");
    const [loading, setLoading] = useState(false);
    const [variant, setVariant] = useState<IVCU | null>(null);

    const handleGenerate = async () => {
        if (!prompt.trim()) return;
        setLoading(true);
        try {
            // In real implementations, use a proper API client
            const res = await fetch("http://localhost:8002/generate/counterfactual", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    base_sdo_id: baseIvcu.id, // Assuming IVCU ID maps to SDO ID
                    prompt: prompt,
                    user_id: "test_user"
                })
            });

            if (res.ok) {
                const data = await res.json();
                // Construct a partial IVCU from response
                const newIvcu: IVCU = {
                    ...baseIvcu,
                    id: data.sdo_id,
                    code: data.selected_code,
                    status: data.status,
                    intent: `Variant: ${prompt}`,
                    confidence: data.confidence,
                    timestamp: Date.now()
                };
                setVariant(newIvcu);
            }
        } catch (e) {
            console.error("Counterfactual failed", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-10">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-6xl h-[85vh] bg-[#0a0a0a] border border-white/10 rounded-3xl overflow-hidden flex flex-col shadow-2xl relative"
            >
                {/* Header */}
                <div className="h-16 border-b border-white/10 bg-white/5 flex items-center justify-between px-8">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
                            <GitFork size={20} />
                        </div>
                        <h2 className="text-lg font-bold text-slate-200 tracking-wide">Counterfactual Explorer</h2>
                    </div>
                    <Button variant="tertiary" size="sm" icon={X} onClick={onClose}>Close</Button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Sidebar / Controls */}
                    <div className="w-1/3 border-r border-white/10 p-8 flex flex-col gap-8 bg-black/20">
                        <div className="space-y-4">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Base Context</label>
                            <div className="p-4 rounded-xl border border-white/10 bg-white/5 text-sm text-slate-400 italic">
                                "{baseIvcu.intent}"
                            </div>
                        </div>

                        <div className="space-y-4 flex-1">
                            <label className="text-xs font-bold text-purple-400 uppercase tracking-widest flex items-center gap-2">
                                <Zap size={12} />
                                What If Parameter
                            </label>
                            <textarea
                                value={prompt}
                                onChange={e => setPrompt(e.target.value)}
                                placeholder="e.g., 'What if we used async/await instead of callbacks?' or 'Refactor to use a Factory pattern'"
                                className="w-full h-48 bg-black/40 border border-white/10 rounded-xl p-4 text-slate-200 focus:ring-1 focus:ring-purple-500/50 outline-none resize-none transition-all placeholder:text-slate-700"
                            />
                            <Button
                                variant="primary"
                                size="lg"
                                icon={loading ? RefreshCw : GitFork}
                                loading={loading}
                                onClick={handleGenerate}
                                className="w-full bg-purple-600 border-purple-500 hover:bg-purple-500"
                            >
                                Explore Variant
                            </Button>
                        </div>
                    </div>

                    {/* Comparison View */}
                    <div className="flex-1 bg-[#111] relative overflow-hidden flex flex-col">
                        {variant ? (
                            <div className="flex-1 flex flex-col">
                                <div className="h-12 border-b border-white/5 flex items-center px-6 gap-4 bg-white/[0.02]">
                                    <span className="text-xs font-bold text-slate-500 uppercase">Comparison Mode</span>
                                    <div className="flex items-center gap-2 text-xs text-slate-300">
                                        <span className="w-2 h-2 rounded-full bg-slate-600"></span> Original
                                        <ArrowRight size={12} className="text-slate-600" />
                                        <span className="w-2 h-2 rounded-full bg-purple-500"></span> Variant
                                    </div>
                                    <div className="ml-auto">
                                        <Button variant="secondary" size="sm" icon={Check} onClick={() => onApply(variant)}>Apply This Logic</Button>
                                    </div>
                                </div>
                                <div className="flex-1 flex overflow-hidden">
                                    <div className="flex-1 border-r border-white/5 p-6 overflow-auto custom-scroll opacity-60 hover:opacity-100 transition-opacity">
                                        <pre className="font-mono text-xs text-slate-400 whitespace-pre-wrap">{baseIvcu.code}</pre>
                                    </div>
                                    <div className="flex-1 p-6 overflow-auto custom-scroll bg-purple-500/[0.02]">
                                        <pre className="font-mono text-xs text-slate-200 whitespace-pre-wrap">{variant.code}</pre>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="flex-1 flex flex-col items-center justify-center text-slate-600 gap-4">
                                <Split size={48} className="opacity-20" />
                                <p className="text-sm font-mono uppercase tracking-widest">Awaiting Simulation Parameters</p>
                            </div>
                        )}
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default CounterfactualPanel;
