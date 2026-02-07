'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAxiomStore } from '@/store/axiom';
import { Send, Loader2, Sparkles, Lightbulb, DollarSign, AlertCircle, ArrowRight, Zap, Play, Users, RotateCcw, RotateCw } from 'lucide-react';

// Mock active users for Phase 4 demo
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

    // Debounced intent parsing & cost estimation
    useEffect(() => {
        if (rawIntent.length < 10) {
            setParsedIntent({}, 0, []);
            setCostEstimate(null);
            setBudgetWarning(null);
            return;
        }

        const timer = setTimeout(async () => {
            if (!token) return; // Wait for auth

            setIsParsing(true);
            try {
                // Parse Intent
                const parseRes = await fetch('/api/v1/intent/parse', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ raw_intent: rawIntent }),
                });

                if (parseRes.ok) {
                    const data = await parseRes.json();
                    setParsedIntent(
                        data.parsed_intent || {},
                        data.confidence || 0,
                        data.suggested_refinements || []
                    );
                }

                // Estimate Cost
                const costRes = await fetch('/api/v1/cost/estimate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        intent: rawIntent,
                        language: selectedLanguage,
                        candidate_count: candidateCount
                    }),
                });

                if (costRes.ok) {
                    const costData = await costRes.json();
                    setCostEstimate({
                        estimatedCostUsd: costData.estimated_cost_usd,
                        inputTokens: costData.input_tokens,
                        outputTokens: costData.output_tokens,
                        embeddingTokens: costData.embedding_tokens,
                        model: costData.model
                    });

                    // Ideally check budget here too, but we'll do it on generate
                    if (costData.estimated_cost_usd > 0.5) {
                        setBudgetWarning("High estimated cost");
                    } else {
                        setBudgetWarning(null);
                    }
                }

            } catch (error) {
                console.error('Analysis error:', error);
            } finally {
                setIsParsing(false);
            }
        }, 800);

        return () => clearTimeout(timer);
    }, [rawIntent, selectedLanguage, candidateCount, setParsedIntent, setCostEstimate, setBudgetWarning, token]);

    // Undo/Redo Handlers
    const handleUndo = async () => {
        if (!currentIVCU?.id || !token) return;
        try {
            const res = await fetch(`/api/v1/undo/${currentIVCU.id}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.previous_state) {
                    const sdo = data.previous_state;
                    setCurrentIVCU({
                        id: sdo.id,
                        rawIntent: sdo.raw_intent,
                        parsedIntent: sdo.parsed_intent,
                        code: sdo.code,
                        language: sdo.language,
                        confidence: sdo.confidence_score,
                        status: sdo.status,
                        contracts: sdo.contracts,
                        verificationResult: sdo.verification_result,
                        candidates: [], // Or fetch? Main concern is state.

                    });
                    setRawIntent(sdo.raw_intent);
                }
            }
        } catch (e) {
            console.error("Undo failed", e);
        }
    };

    const handleRedo = async () => {
        if (!currentIVCU?.id || !token) return;
        try {
            const res = await fetch(`/api/v1/redo/${currentIVCU.id}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.previous_state) { // API returns 'previous_state' field for both undo/redo per my check
                    const sdo = data.previous_state;
                    setCurrentIVCU({
                        id: sdo.id,
                        rawIntent: sdo.raw_intent,
                        parsedIntent: sdo.parsed_intent,
                        code: sdo.code,
                        language: sdo.language,
                        confidence: sdo.confidence_score,
                        status: sdo.status,
                        contracts: sdo.contracts,
                        verificationResult: sdo.verification_result,
                        candidates: [],
                    });
                    setRawIntent(sdo.raw_intent);
                }
            }
        } catch (e) {
            console.error("Redo failed", e);
        }
    };

    const handleGenerate = async () => {
        if (!rawIntent.trim() || isGenerating || !token) return;

        setIsGenerating(true);

        // Optimistic UI update
        const tempId = crypto.randomUUID();
        setCurrentIVCU({
            id: tempId,
            rawIntent,
            parsedIntent,
            code: null,
            language: selectedLanguage,
            confidence: 0,
            status: 'generating' as const,
            contracts: [],
            verificationResult: null,
        });

        try {
            // 1. Create IVCU
            // Ensure we have a valid project ID
            const projectId = currentProject?.id || '123e4567-e89b-12d3-a456-426614174000';

            const createRes = await fetch('/api/v1/intent/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    project_id: projectId,
                    raw_intent: rawIntent,
                    contracts: []
                })
            });

            if (!createRes.ok) {
                throw new Error(await createRes.text());
            }

            const createData = await createRes.json();
            const realId = createData.ivcu_id;

            // 2. Start Generation (Async via Temporal)
            const startRes = await fetch('/api/v1/generation/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    ivcu_id: realId,
                    language: selectedLanguage,
                    candidate_count: candidateCount,
                    strategy: candidateCount > 1 ? 'parallel' : 'simple'
                }),
            });

            if (!startRes.ok) {
                throw new Error(await startRes.text());
            }

            // 3. Poll for status
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/api/v1/generation/${realId}/status`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    if (!statusRes.ok) return;

                    const statusData = await statusRes.json();

                    if (statusData.status === 'verified') {
                        clearInterval(pollInterval);

                        const resultRes = await fetch(`/api/v1/intent/${realId}`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                        });

                        if (resultRes.ok) {
                            const ivcu = await resultRes.json();

                            setCurrentIVCU({
                                id: ivcu.id,
                                rawIntent: ivcu.raw_intent,
                                parsedIntent: ivcu.parsed_intent,
                                code: ivcu.code,
                                language: ivcu.language || selectedLanguage,
                                confidence: ivcu.confidence_score,
                                status: 'verified',
                                contracts: ivcu.contracts || [],
                                verificationResult: ivcu.verification_result || null,
                                candidates: [],
                                selectedCandidateId: undefined,
                                costUsd: 0
                            });
                        }
                        setIsGenerating(false);
                    } else if (statusData.status === 'failed') {
                        clearInterval(pollInterval);
                        throw new Error('Generation failed');
                    }
                    // For feedback, we could pulse updates here if backend provided progress
                } catch (err) {
                    console.error("Polling error", err);
                    clearInterval(pollInterval);
                    setIsGenerating(false);
                }
            }, 1000);

        } catch (error) {
            console.error('Generation error:', error);
            setCurrentIVCU({
                id: tempId,
                rawIntent,
                parsedIntent,
                code: null,
                language: selectedLanguage,
                confidence: 0,
                status: 'failed',
                contracts: [],
                verificationResult: null
            });
            setIsGenerating(false);
        }
    };

    return (
        <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-2 text-axiom-400">
                        <Sparkles className="w-5 h-5" />
                        <span className="font-semibold tracking-wide uppercase text-sm">Intent Canvas</span>
                    </div>

                    {/* Active Collaborators (Phase 4) */}
                    <div className="flex items-center gap-2">
                        <div className="flex -space-x-2">
                            {activeUsers.map(user => (
                                <div key={user.id} className={`w-6 h-6 rounded-full ${user.color} border border-black flex items-center justify-center text-[10px] font-bold text-white`} title={`${user.name} is editing`}>
                                    {user.name[0]}
                                </div>
                            ))}
                        </div>
                        <span className="text-xs text-gray-500 px-2">+ You</span>
                    </div>

                    {/* Undo/Redo Controls */}
                    <div className="flex items-center gap-1 ml-4 border-l border-white/10 pl-4">
                        <motion.button
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={handleUndo}
                            disabled={!currentIVCU?.id || isGenerating}
                            className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            title="Undo"
                        >
                            <RotateCcw className="w-4 h-4" />
                        </motion.button>
                        <motion.button
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={handleRedo}
                            disabled={!currentIVCU?.id || isGenerating}
                            className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            title="Redo"
                        >
                            <RotateCw className="w-4 h-4" />
                        </motion.button>
                    </div>
                </div>

                {isParsing && (
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Analyzing & Estimating...</span>
                    </div>
                )}
            </div>

            {/* Intent Input */}
            <div className="relative mb-4">
                <textarea
                    value={rawIntent}
                    onChange={(e) => setRawIntent(e.target.value)}
                    placeholder="Describe what you want to create...
Example: Create a function that validates email addresses and returns a boolean. It should handle edge cases like missing @ symbol."
                    className="w-full h-40 bg-black/30 border border-white/10 rounded-xl p-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-axiom-500 focus:ring-1 focus:ring-axiom-500/50 transition-all font-mono text-sm"
                    disabled={isGenerating}
                />

                {/* Confidence Indicator */}
                <AnimatePresence>
                    {parseConfidence > 0 && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="absolute top-3 right-3 px-2 py-1 rounded-md text-xs font-medium"
                            style={{
                                backgroundColor: parseConfidence > 0.7
                                    ? 'rgba(34, 197, 94, 0.2)'
                                    : parseConfidence > 0.4
                                        ? 'rgba(245, 158, 11, 0.2)'
                                        : 'rgba(239, 68, 68, 0.2)',
                                color: parseConfidence > 0.7
                                    ? '#22c55e'
                                    : parseConfidence > 0.4
                                        ? '#f59e0b'
                                        : '#ef4444',
                            }}
                        >
                            {Math.round(parseConfidence * 100)}% understood
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Cost Estimate & Budget */}
            <AnimatePresence>
                {costEstimate && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-4 flex items-center justify-between text-xs px-3 py-2 bg-black/20 rounded-lg border border-white/5"
                    >
                        <div className="flex items-center gap-4 text-gray-400">
                            <div className="flex items-center gap-1">
                                <DollarSign className="w-3 h-3 text-emerald-500" />
                                <span>Est. Cost: <span className="text-emerald-400 font-mono">${costEstimate.estimatedCostUsd.toFixed(4)}</span></span>
                            </div>
                            <div>
                                Tokens: <span className="text-gray-300 font-mono">{costEstimate.inputTokens + costEstimate.outputTokens}</span>
                            </div>
                            <div>
                                Model: <span className="text-axiom-400">{costEstimate.model}</span>
                            </div>
                            <div className="flex items-center gap-1 text-blue-400" title="RAG Enabled">
                                <Sparkles className="w-3 h-3" />
                                <span>Memory Active</span>
                            </div>
                        </div>

                        {budgetWarning && (
                            <div className="flex items-center gap-1 text-amber-500">
                                <AlertCircle className="w-3 h-3" />
                                <span>{budgetWarning}</span>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Suggestions */}
            <AnimatePresence>
                {suggestedRefinements.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-4 overflow-hidden"
                    >
                        <div className="flex items-center gap-2 text-sm text-amber-400 mb-2">
                            <Lightbulb className="w-4 h-4" />
                            <span>Suggested refinements:</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {suggestedRefinements.map((refinement, i) => (
                                <button
                                    key={i}
                                    className="text-xs px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-colors"
                                    onClick={() => setRawIntent(rawIntent + '. ' + refinement)}
                                >
                                    + {refinement}
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Language & Generate */}
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-4">
                    <CustomSelect
                        value={selectedLanguage}
                        onChange={(val) => setSelectedLanguage(val)}
                        options={LANGUAGES}
                        disabled={isGenerating}
                    />

                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <span>Candidates:</span>
                        <CustomSelect
                            value={candidateCount}
                            onChange={(val) => setCandidateCount(Number(val))}
                            options={[
                                { value: 1, label: '1' },
                                { value: 3, label: '3' },
                                { value: 5, label: '5' }
                            ]}
                            disabled={isGenerating}
                        />
                    </div>
                </div>

                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleGenerate}
                    disabled={!rawIntent.trim() || isGenerating}
                    className="flex-1 flex items-center justify-center gap-2 bg-axiom-gradient text-white font-medium py-2.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shadow-lg shadow-axiom-500/20"
                >
                    {isGenerating ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>Generating Candidates...</span>
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

function CustomSelect({
    value,
    onChange,
    options,
    disabled = false
}: {
    value: string | number;
    onChange: (value: string) => void;
    options: { value: string | number; label: string }[];
    disabled?: boolean;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const selectedLabel = options.find(o => o.value === value)?.label || value;

    return (
        <div className="relative">
            <button
                type="button"
                onClick={(e) => {
                    if (!disabled) {
                        e.stopPropagation();
                        setIsOpen(!isOpen);
                    }
                }}
                className={`flex items-center gap-2 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white min-w-[100px] justify-between transition-colors ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/5'}`}
            >
                <span>{selectedLabel}</span>
                <span className="text-gray-500 text-xs">▼</span>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        <div
                            className="fixed inset-0 z-10"
                            onClick={() => setIsOpen(false)}
                        />
                        <motion.div
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -5 }}
                            className="absolute top-full text-left left-0 mt-1 w-full min-w-[140px] bg-neutral-900 border border-white/20 rounded-lg shadow-xl shadow-black/50 overflow-hidden z-50"
                        >
                            {options.map((option) => (
                                <button
                                    key={option.value}
                                    type="button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onChange(String(option.value));
                                        setIsOpen(false);
                                    }}
                                    className={`w-full text-left px-4 py-2 text-sm hover:bg-white/20 transition-colors ${option.value === value ? 'text-axiom-400 bg-white/10 font-bold' : 'text-white'}`}
                                >
                                    {option.label}
                                </button>
                            ))}
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
