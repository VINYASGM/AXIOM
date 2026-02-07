'use client';

import { useState, useEffect } from 'react';
import { useAxiomStore } from '@/store/axiom';
import { Send, Sparkles, AlertCircle, DollarSign, Lightbulb } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function ChatPane() {
    const {
        rawIntent, setRawIntent,
        parsedIntent,
        isGenerating,
        costEstimate,
        selectedLanguage,
        analyzeIntent,
        generateCode
    } = useAxiomStore();

    // Debounced Intent Analysis
    useEffect(() => {
        const timer = setTimeout(() => {
            if (rawIntent.length > 5) {
                analyzeIntent(rawIntent);
            }
        }, 800);
        return () => clearTimeout(timer);
    }, [rawIntent, analyzeIntent]);

    const handleGenerate = async () => {
        if (!rawIntent || isGenerating) return;
        await generateCode();
    };

    return (
        <div className="flex flex-col h-full bg-surface/30">
            {/* Header */}
            <div className="p-4 border-b border-white/5 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-axiom-400" />
                <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-300">Intent</h2>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4 space-y-6">

                {/* Input Area */}
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-gray-500 uppercase">Description</label>
                    <textarea
                        value={rawIntent}
                        onChange={(e) => setRawIntent(e.target.value)}
                        placeholder="Describe functionality..."
                        className="w-full h-48 bg-element/50 border border-white/10 rounded-xl p-3 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-axiom-500/50 focus:bg-element transition-all font-mono"
                        disabled={isGenerating}
                    />
                </div>

                {/* Suggestions */}
                <AnimatePresence>
                    {rawIntent.length > 5 && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="space-y-2"
                        >
                            <div className="flex items-center gap-2 text-xs text-amber-500 font-medium">
                                <Lightbulb className="w-3 h-3" />
                                <span>Refinements</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {["Add input validation", "Handle timeouts", "Log metrics"].map((s, i) => (
                                    <button
                                        key={i}
                                        onClick={() => setRawIntent(rawIntent + "\n- " + s)}
                                        className="text-[10px] px-2 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded-md hover:bg-amber-500/20 transition-colors text-left"
                                    >
                                        + {s}
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Cost Estimation */}
                {costEstimate && (
                    <div className="p-3 bg-black/20 rounded-lg border border-white/5 space-y-2">
                        <div className="flex items-center justify-between text-xs text-gray-400">
                            <span>Est. Cost</span>
                            <span className="text-emerald-400 font-mono">${costEstimate.estimatedCostUsd}</span>
                        </div>
                        <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                            <div className="bg-emerald-500 h-full w-[20%]" />
                        </div>
                    </div>
                )}
            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-white/5 bg-surface/50">
                <button
                    onClick={handleGenerate}
                    disabled={!rawIntent || isGenerating}
                    className="w-full flex items-center justify-center gap-2 bg-axiom-600 hover:bg-axiom-500 text-white font-medium py-2.5 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-axiom-900/50"
                >
                    {isGenerating ? (
                        <span>Generating...</span>
                    ) : (
                        <>
                            <Send className="w-4 h-4" />
                            <span>Generate Code</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
