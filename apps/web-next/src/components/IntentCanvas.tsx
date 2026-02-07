'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAxiomStore } from '@/store/axiom';
import { Send, Loader2, Sparkles, Lightbulb, DollarSign, AlertCircle, RotateCcw, RotateCw } from 'lucide-react';

const activeUsers = [
    { id: '1', name: 'Alice', color: 'bg-purple-500' },
    { id: '2', name: 'Bob', color: 'bg-green-500' }
];

const LANGUAGES = [
    { value: 'typescript', label: 'TypeScript' },
    { value: 'python', label: 'Python' },
    { value: 'go', label: 'Go' },
];

export function IntentCanvas() {
    const {
        rawIntent,
        setRawIntent,
        selectedLanguage,
        setSelectedLanguage,
        parsedIntent,
        parseConfidence,
        suggestedRefinements,
        setParsedIntent,
        setIsGenerating,
        currentIVCU,
        setCurrentIVCU,
        isGenerating,
        token,
        costEstimate,
        setCostEstimate,
        budgetWarning,
        setBudgetWarning,
        currentProject,
    } = useAxiomStore();

    const [isParsing, setIsParsing] = useState(false);
    const [candidateCount, setCandidateCount] = useState(3);

    const { analyzeIntent, generateCode } = useAxiomStore();

    useEffect(() => {
        if (rawIntent.length < 5) return;

        const timer = setTimeout(() => {
            setIsParsing(true);
            analyzeIntent(rawIntent).then(() => setIsParsing(false));
            // costEstimate is handled inside analyzeIntent now
        }, 800);

        return () => clearTimeout(timer);
    }, [rawIntent, analyzeIntent]);

    const handleGenerate = async () => {
        if (!rawIntent.trim() || isGenerating) return;
        await generateCode();
    };

    return (
        <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2 text-blue-400">
                    <Sparkles className="w-5 h-5" />
                    <span className="font-semibold tracking-wide uppercase text-sm">Intent Canvas</span>
                </div>
                {isParsing && (
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Analyzing...</span>
                    </div>
                )}
            </div>

            <div className="relative mb-4">
                <textarea
                    value={rawIntent}
                    onChange={(e) => setRawIntent(e.target.value)}
                    placeholder="Describe what you want to create..."
                    className="w-full h-40 bg-black/30 border border-white/10 rounded-xl p-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all font-mono text-sm"
                    disabled={isGenerating}
                />
                <AnimatePresence>
                    {parseConfidence > 0 && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="absolute top-3 right-3 px-2 py-1 rounded-md text-xs font-medium bg-green-500/20 text-green-400"
                        >
                            {Math.round(parseConfidence * 100)}% understood
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                    <CustomSelect
                        value={selectedLanguage}
                        onChange={(val: string) => setSelectedLanguage(val)}
                        options={LANGUAGES}
                        disabled={isGenerating}
                    />
                </div>

                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleGenerate}
                    disabled={!rawIntent.trim() || isGenerating}
                    className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-xl disabled:opacity-50 transition-colors"
                >
                    {isGenerating ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>Generating...</span>
                        </>
                    ) : (
                        <>
                            <Send className="w-5 h-5" />
                            <span>Generate Code</span>
                        </>
                    )}
                </motion.button>
            </div>
        </div>
    );
}

function CustomSelect({ value, onChange, options, disabled }: any) {
    const [isOpen, setIsOpen] = useState(false);
    const selectedLabel = options.find((o: any) => o.value === value)?.label || value;

    return (
        <div className="relative">
            <button
                type="button"
                onClick={() => !disabled && setIsOpen(!isOpen)}
                className="flex items-center gap-2 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white min-w-[120px] justify-between"
            >
                <span>{selectedLabel}</span>
                <span className="text-gray-500 text-xs">▼</span>
            </button>
            {isOpen && (
                <>
                    <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
                    <div className="absolute top-full left-0 mt-1 w-full bg-neutral-900 border border-white/20 rounded-lg shadow-xl overflow-hidden z-20">
                        {options.map((option: any) => (
                            <button
                                key={option.value}
                                onClick={() => { onChange(option.value); setIsOpen(false); }}
                                className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10"
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}
