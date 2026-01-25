'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useAxiomStore, IVCU, Candidate } from '@/store/axiom';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { VerificationBreakdown } from './VerificationBreakdown';
import { Code2, FileCode, CheckCircle2, XCircle, Copy, Download, CornerUpLeft, AlertTriangle, RotateCcw } from 'lucide-react';
import { useState } from 'react';

export function ReviewPanel() {
    const { currentIVCU, isGenerating, setCurrentIVCU } = useAxiomStore();
    const [activeTab, setActiveTab] = useState<'code' | 'verification' | 'sources'>('code');
    const [copied, setCopied] = useState(false);

    const copyCode = () => {
        if (currentIVCU?.code) {
            navigator.clipboard.writeText(currentIVCU.code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const downloadCode = () => {
        if (currentIVCU?.code) {
            const extension = currentIVCU.language === 'typescript' ? 'ts'
                : currentIVCU.language === 'python' ? 'py'
                    : 'go';
            const blob = new Blob([currentIVCU.code], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `generated.${extension}`;
            a.click();
            URL.revokeObjectURL(url);
        }
    };

    const [undoLoading, setUndoLoading] = useState(false);
    const [undoMessage, setUndoMessage] = useState<string | null>(null);

    const handleUndo = async () => {
        if (!currentIVCU?.id) return;

        setUndoLoading(true);
        setUndoMessage(null);

        try {
            // Call the Python AI service undo endpoint
            const res = await fetch(`http://localhost:8002/undo/${currentIVCU.id}`, {
                method: 'POST'
            });
            const data = await res.json();

            if (data.success && data.previous_state) {
                // Update the store with previous state
                setCurrentIVCU(data.previous_state);
                setUndoMessage('Restored previous state');
            } else {
                setUndoMessage(data.message || 'No previous state available');
            }
        } catch (error) {
            console.error("Undo failed", error);
            setUndoMessage('Undo failed');
        } finally {
            setUndoLoading(false);
            setTimeout(() => setUndoMessage(null), 3000);
        }
    };

    return (
        <div className="glass rounded-2xl p-6 h-full flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Code2 className="w-5 h-5 text-axiom-400" />
                    <h2 className="text-lg font-semibold text-white">Review Panel</h2>
                </div>

                {currentIVCU && (
                    <div className="flex items-center gap-2">
                        <StatusBadge status={currentIVCU.status} />
                        <ConfidenceIndicator confidence={currentIVCU.confidence} size="sm" />
                        <button
                            onClick={handleUndo}
                            disabled={undoLoading}
                            className={`p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors ml-2 ${undoLoading ? 'opacity-50 cursor-wait' : ''}`}
                            title="Undo last generation"
                        >
                            {undoLoading ? (
                                <RotateCcw className="w-4 h-4 animate-spin" />
                            ) : (
                                <CornerUpLeft className="w-4 h-4" />
                            )}
                        </button>
                        {undoMessage && (
                            <span className="text-xs text-gray-400 ml-2">{undoMessage}</span>
                        )}
                    </div>
                )}
            </div>

            {currentIVCU && !isGenerating && (
                <div className="flex gap-1 bg-white/5 p-1 rounded-lg mb-4 shrink-0">
                    <button
                        onClick={() => setActiveTab('code')}
                        className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'code' ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Code
                    </button>
                    <button
                        onClick={() => setActiveTab('verification')}
                        className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'verification' ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Verification
                    </button>
                    <button
                        onClick={() => setActiveTab('sources')}
                        className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'sources' ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Sources
                    </button>
                </div>
            )}

            <AnimatePresence mode="wait">
                {!currentIVCU && !isGenerating ? (
                    <motion.div
                        key="empty"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center justify-center flex-1 text-gray-500"
                    >
                        <FileCode className="w-16 h-16 mb-4 opacity-30" />
                        <p className="text-center">
                            Enter your intent and click Generate
                            <br />
                            <span className="text-sm text-gray-600">
                                Verified code will appear here
                            </span>
                        </p>
                    </motion.div>
                ) : isGenerating ? (
                    <motion.div
                        key="generating"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center justify-center flex-1"
                    >
                        {/* Generation Loader - kept same */}
                        <div className="relative w-20 h-20 mb-6">
                            <motion.div
                                className="absolute inset-0 rounded-full bg-axiom-500/20"
                                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                                transition={{ duration: 2, repeat: Infinity }}
                            />
                            <motion.div
                                className="absolute inset-2 rounded-full bg-axiom-500/30"
                                animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
                                transition={{ duration: 2, repeat: Infinity, delay: 0.2 }}
                            />
                            <motion.div
                                className="absolute inset-4 rounded-full bg-axiom-gradient flex items-center justify-center"
                                animate={{ rotate: 360 }}
                                transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                            >
                                <Code2 className="w-6 h-6 text-white" />
                            </motion.div>
                        </div>
                        <GenerationStages status={currentIVCU?.status || 'generating'} />
                    </motion.div>
                ) : currentIVCU ? (
                    <motion.div
                        key="content"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="flex flex-col h-full min-h-0"
                    >
                        {activeTab === 'code' && (
                            <>
                                {/* Code Actions */}
                                <div className="flex items-center justify-between mb-3 shrink-0">
                                    <span className="text-sm text-gray-400">
                                        {currentIVCU.language.charAt(0).toUpperCase() + currentIVCU.language.slice(1)}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={copyCode}
                                            className="p-2 rounded-lg hover:bg-white/10 transition-colors text-gray-400 hover:text-white"
                                            title="Copy code"
                                        >
                                            <Copy className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={downloadCode}
                                            className="p-2 rounded-lg hover:bg-white/10 transition-colors text-gray-400 hover:text-white"
                                            title="Download"
                                        >
                                            <Download className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                {/* Code Block */}
                                <div className="relative flex-1 min-h-0 mb-4">
                                    <pre className="code-block h-full overflow-auto rounded-xl p-4 bg-black/30 border border-white/5">
                                        <code className="text-gray-300 font-mono text-sm">{currentIVCU.code}</code>
                                    </pre>
                                    <AnimatePresence>
                                        {copied && (
                                            <motion.div
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0 }}
                                                className="absolute top-2 right-2 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded"
                                            >
                                                Copied!
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>

                                {/* Candidates List if multiple */}
                                {currentIVCU.candidates && currentIVCU.candidates.length > 1 && (
                                    <div className="flex gap-2 text-xs overflow-x-auto pb-1 shrink-0">
                                        {currentIVCU.candidates.map((c, i) => (
                                            <div
                                                key={c.id}
                                                className={`px-2 py-1 rounded border whitespace-nowrap ${c.id === currentIVCU.selectedCandidateId
                                                    ? 'bg-axiom-500/20 border-axiom-500/50 text-axiom-300'
                                                    : 'bg-white/5 border-white/10 text-gray-500'
                                                    }`}
                                            >
                                                Cand {i + 1} ({Math.round(c.verificationScore * 100)}%)
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}

                        {activeTab === 'verification' && (
                            <div className="flex-1 overflow-auto space-y-4 pr-2">
                                {/* Overall Result */}
                                {currentIVCU.verificationResult && (
                                    <div className={`p-4 rounded-xl border ${currentIVCU.verificationResult.passed
                                        ? 'bg-green-500/10 border-green-500/20'
                                        : 'bg-amber-500/10 border-amber-500/20'
                                        }`}>
                                        <div className="flex items-center gap-3 mb-2">
                                            {currentIVCU.verificationResult.passed ?
                                                <CheckCircle2 className="w-6 h-6 text-green-400" /> :
                                                <AlertTriangle className="w-6 h-6 text-amber-400" />
                                            }
                                            <div>
                                                <h3 className={`font-semibold ${currentIVCU.verificationResult.passed ? 'text-green-400' : 'text-amber-400'}`}>
                                                    {currentIVCU.verificationResult.passed ? 'Verified Safe' : 'Verification Failed'}
                                                </h3>
                                                <p className="text-xs text-gray-400">
                                                    Confidence: {Math.round(currentIVCU.confidence * 100)}%
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Individual Verifiers */}
                                {currentIVCU.verificationResult?.verifierResults.map((v, i) => (
                                    <div key={i} className="bg-black/20 rounded-xl p-4 border border-white/5">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                {v.passed ?
                                                    <CheckCircle2 className="w-4 h-4 text-green-400" /> :
                                                    <XCircle className="w-4 h-4 text-red-400" />
                                                }
                                                <span className="font-medium text-gray-200 capitalize">
                                                    {v.name.replace(/_/g, ' ')}
                                                </span>
                                                <span className="text-xs px-1.5 py-0.5 rounded bg-white/5 text-gray-500 uppercase">
                                                    {v.tier.replace('_', ' ')}
                                                </span>
                                            </div>
                                            <span className="text-xs text-gray-500">{Math.round(v.durationMs)}ms</span>
                                        </div>

                                        {/* Unit Test Details */}
                                        {v.name === 'unit_tests' && v.details && (
                                            <div className="mt-2 space-y-2">
                                                {v.details.output && (
                                                    <div className="bg-black/40 rounded p-2 overflow-x-auto">
                                                        <pre className="text-xs font-mono text-gray-400 leading-tight">
                                                            {v.details.output}
                                                        </pre>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Standard Messages */}
                                        {v.messages.length > 0 && (
                                            <ul className="mt-2 text-sm text-gray-400 space-y-1 list-disc list-inside">
                                                {v.messages.map((m, j) => <li key={j}>{m}</li>)}
                                            </ul>
                                        )}
                                        {v.errors && v.errors.length > 0 && (
                                            <ul className="mt-2 text-sm text-red-400 space-y-1 list-disc list-inside">
                                                {v.errors.map((e, j) => <li key={j}>{e}</li>)}
                                            </ul>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {activeTab === 'sources' && (
                            <div className="flex-1 overflow-auto space-y-4 pr-2">
                                {currentIVCU.retrievedContext?.codeChunks.length ? (
                                    currentIVCU.retrievedContext.codeChunks.map((chunk, i) => (
                                        <div key={i} className="bg-black/20 rounded-xl p-4 border border-white/5">
                                            <div className="flex items-center gap-2 mb-2">
                                                <FileCode className="w-4 h-4 text-axiom-400" />
                                                <span className="text-sm font-medium text-gray-300 truncate">
                                                    {chunk.filePath}
                                                </span>
                                            </div>
                                            <pre className="bg-black/30 rounded p-2 overflow-x-auto">
                                                <code className="text-xs font-mono text-gray-400 block max-h-32 overflow-y-auto">
                                                    {chunk.content}
                                                </code>
                                            </pre>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center text-gray-500 py-8">
                                        <p>No RAG context used for this generation.</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                        key="error"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex flex-col items-center justify-center h-[400px] text-red-400"
                    >
                        <XCircle className="w-16 h-16 mb-4 opacity-50" />
                        <p>Generation failed. Please try again.</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const colors = {
        draft: 'bg-gray-500/20 text-gray-400',
        generating: 'bg-blue-500/20 text-blue-400',
        verifying: 'bg-amber-500/20 text-amber-400',
        verified: 'bg-green-500/20 text-green-400',
        failed: 'bg-red-500/20 text-red-400',
    };

    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status as keyof typeof colors] || colors.draft}`}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
    );
}

function GenerationStages({ status }: { status: string }) {
    const stages = [
        { key: 'generating', label: 'Generating candidates...' },
        { key: 'verifying', label: 'Running verification tier 1...' },
        { key: 'verified', label: 'Finalizing selection...' },
    ];

    const currentIndex = stages.findIndex(s => s.key === status);
    // If status is not in list (e.g. 'failed'), default to last
    const activeIndex = currentIndex === -1 ? 0 : currentIndex;

    return (
        <div className="space-y-2 text-center">
            {stages.map((stage, i) => (
                <div
                    key={stage.key}
                    className={`text-sm ${i <= activeIndex ? 'text-axiom-400' : 'text-gray-600'}`}
                >
                    {i < activeIndex && '✓ '}
                    {stage.label}
                </div>
            ))}
        </div>
    );
}
