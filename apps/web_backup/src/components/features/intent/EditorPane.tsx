'use client';

import { useEffect, useRef, useState } from 'react';
import Editor, { useMonaco } from '@monaco-editor/react';
import { useAxiomStore } from '@/store/axiom';
import { Loader2, Play, Code2, FileDiff, Download } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function EditorPane() {
    const { currentIVCU, isGenerating, selectedLanguage } = useAxiomStore();
    const [activeTab, setActiveTab] = useState<'code' | 'diff'>('code');
    const monaco = useMonaco();

    useEffect(() => {
        if (monaco) {
            // Configure Monaco theme to match AXIOM Zinc-950
            monaco.editor.defineTheme('axiom-dark', {
                base: 'vs-dark',
                inherit: true,
                rules: [],
                colors: {
                    'editor.background': '#09090B', // Zinc-950 / bg-canvas
                    'editor.lineHighlightBackground': '#18181B',
                    'editorGutter.background': '#09090B',
                }
            });
            monaco.editor.setTheme('axiom-dark');
        }
    }, [monaco]);

    return (
        <div className="flex flex-col h-full relative group">
            {/* Toolbar */}
            <div className="h-10 border-b border-white/5 flex items-center justify-between px-4 bg-surface/30">
                <div className="flex items-center gap-1">
                    <TabButton
                        active={activeTab === 'code'}
                        onClick={() => setActiveTab('code')}
                        icon={Code2}
                        label="Code"
                    />
                    <TabButton
                        active={activeTab === 'diff'}
                        onClick={() => setActiveTab('diff')}
                        icon={FileDiff}
                        label="Diff"
                    />
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">
                        {selectedLanguage.toUpperCase()}
                    </span>
                    {currentIVCU && currentIVCU.confidence > 0 && (
                        <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${currentIVCU.confidence > 0.8 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                            }`}>
                            {(currentIVCU.confidence * 100).toFixed(0)}% CONFIDENCE
                        </div>
                    )}
                </div>
            </div>

            {/* Editor Area */}
            <div className="flex-1 relative bg-canvas">
                {isGenerating ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 gap-4">
                        <div className="relative">
                            <motion.div
                                className="absolute inset-0 bg-axiom-500/20 blur-xl rounded-full"
                                animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
                                transition={{ duration: 2, repeat: Infinity }}
                            />
                            <Loader2 className="w-8 h-8 animate-spin text-axiom-400 relative z-10" />
                        </div>
                        <p className="font-mono text-xs animate-pulse">Generating Candidate Blocks...</p>
                    </div>
                ) : (
                    activeTab === 'code' ? (
                        <Editor
                            height="100%"
                            language={selectedLanguage || 'python'}
                            value={currentIVCU?.code || '# Generated code will appear here...'}
                            theme="axiom-dark"
                            options={{
                                minimap: { enabled: false },
                                fontSize: 13,
                                fontFamily: 'JetBrains Mono, monospace',
                                fontLigatures: true,
                                scrollBeyondLastLine: false,
                                automaticLayout: true,
                                padding: { top: 16 }
                            }}
                        />
                    ) : (
                        <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                            Diff View Implementation Pending
                        </div>
                    )
                )}
            </div>
        </div>
    );
}

function TabButton({ active, onClick, icon: Icon, label }: { active: boolean, onClick: () => void, icon: any, label: string }) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${active ? 'text-white bg-white/10' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
        >
            <Icon className="w-3.5 h-3.5" />
            {label}
        </button>
    );
}
