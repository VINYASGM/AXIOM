'use client';

import { useSDEStore } from '@/store/sde';
import { useAxiomStore } from '@/store/axiom';
import { motion, AnimatePresence } from 'framer-motion';
import { Code2, GitCommit, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import Editor from '@monaco-editor/react';

export function HolographicLens() {
    const { lensTargetId, isLensActive } = useSDEStore();
    const { currentIVCU } = useAxiomStore(); // Ideally this would fetch based on ID
    const [copied, setCopied] = useState(false);

    // Mock data fetching since we don't have a map of IVCUs in store yet, just 'currentIVCU'.
    // In production this would query a cache by ID.
    const code = (currentIVCU?.id === lensTargetId) ? currentIVCU.code : "# Code projection unavailable for this node.";
    const language = (currentIVCU?.id === lensTargetId && currentIVCU.language) ? currentIVCU.language : "python";

    if (!lensTargetId || !isLensActive) return null;

    const handleCopy = () => {
        if (code) navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="absolute top-4 right-4 w-[500px] h-[600px] bg-black/80 backdrop-blur-3xl rounded-2xl border border-white/10 shadow-2xl z-50 overflow-hidden flex flex-col"
            >
                {/* Lens Header */}
                <div className="h-10 bg-white/5 border-b border-white/5 flex items-center justify-between px-4">
                    <div className="flex items-center gap-2">
                        <Code2 className="w-4 h-4 text-axiom-400" />
                        <span className="text-xs font-mono text-gray-300 uppercase tracking-widest">Holographic Projection</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <button onClick={handleCopy} className="p-1 hover:bg-white/10 rounded">
                            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-500" />}
                        </button>
                    </div>
                </div>

                {/* Code Content */}
                <div className="flex-1 relative">
                    <Editor
                        height="100%"
                        language={language}
                        value={code || ""}
                        theme="axiom-dark" // Ensure theme definition is global or re-defined here
                        options={{
                            minimap: { enabled: false },
                            fontSize: 12,
                            fontFamily: 'JetBrains Mono',
                            readOnly: true,
                            domReadOnly: true,
                            renderLineHighlight: 'none',
                        }}
                    />

                    {/* Overlay Scanlines */}
                    <div className="absolute inset-0 pointer-events-none bg-[url('/scanlines.png')] opacity-10" />
                    <div className="absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent to-black/40" />
                </div>

                {/* Footer Metadata */}
                <div className="h-8 bg-black/60 border-t border-white/5 flex items-center px-4 gap-4 text-[10px] text-gray-500 font-mono">
                    <div className="flex items-center gap-1">
                        <GitCommit className="w-3 h-3" />
                        <span>SHA: 7a82b91</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span>Verified</span>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
