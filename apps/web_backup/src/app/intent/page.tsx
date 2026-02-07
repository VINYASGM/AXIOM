'use client';

import { useState } from 'react';
// import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { ChatPane } from '@/components/features/intent/ChatPane';
import { EditorPane } from '@/components/features/intent/EditorPane';
import { InspectorPane } from '@/components/features/intent/InspectorPane';
import { GraphVisualization } from '@/components/features/intent/GraphVisualization';
import { useAxiomStore } from '@/store/axiom';
import { ShieldCheck, Network, X } from 'lucide-react';
import clsx from 'clsx';

export default function IntentStudioPage() {
    const { currentIVCU } = useAxiomStore();
    const [showRightPanel, setShowRightPanel] = useState(true);
    const [rightPanelMode, setRightPanelMode] = useState<'inspector' | 'graph'>('inspector');

    return (
        <div className="h-full bg-canvas text-white overflow-hidden">
            <div className="grid grid-cols-12 h-full">
                {/* Left: Chat / Intent (25%) */}
                <div className="col-span-3 border-r border-white/5 h-full overflow-hidden flex flex-col bg-surface/30">
                    <ChatPane />
                </div>

                {/* Center: Code / Diff */}
                <div className={`${showRightPanel ? 'col-span-6' : 'col-span-9'} h-full overflow-hidden flex flex-col relative transition-all duration-300`}>
                    <EditorPane />
                </div>

                {/* Right: Inspector / Graph */}
                {showRightPanel && (
                    <div className="col-span-3 border-l border-white/5 h-full overflow-hidden bg-surface/50 flex flex-col">
                        <div className="min-h-[40px] border-b border-white/5 flex items-center justify-between px-2 bg-black/20">
                            <div className="flex gap-1">
                                <button
                                    onClick={() => setRightPanelMode('inspector')}
                                    className={clsx(
                                        "flex items-center gap-2 px-3 py-1.5 rounded-t-lg text-xs font-medium transition-colors border-b-2",
                                        rightPanelMode === 'inspector'
                                            ? "border-emerald-500 text-white bg-white/5"
                                            : "border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5"
                                    )}
                                >
                                    <ShieldCheck className="w-3.5 h-3.5" />
                                    <span>Inspector</span>
                                </button>
                                <button
                                    onClick={() => setRightPanelMode('graph')}
                                    className={clsx(
                                        "flex items-center gap-2 px-3 py-1.5 rounded-t-lg text-xs font-medium transition-colors border-b-2",
                                        rightPanelMode === 'graph'
                                            ? "border-blue-500 text-white bg-white/5"
                                            : "border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5"
                                    )}
                                >
                                    <Network className="w-3.5 h-3.5" />
                                    <span>Knowledge Graph</span>
                                </button>
                            </div>
                            <button
                                onClick={() => setShowRightPanel(false)}
                                className="p-1.5 text-gray-500 hover:text-white rounded-md hover:bg-white/10 transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-hidden relative">
                            {rightPanelMode === 'inspector' ? (
                                <InspectorPane onClose={() => setShowRightPanel(false)} />
                            ) : (
                                <GraphVisualization />
                            )}
                        </div>
                    </div>
                )}

                {/* Re-open button if closed */}
                {!showRightPanel && (
                    <div className="absolute top-4 right-4 z-50">
                        <button
                            onClick={() => setShowRightPanel(true)}
                            className="bg-axiom-600 p-2 rounded-lg shadow-xl text-white hover:bg-axiom-500 transition-colors"
                        >
                            <ShieldCheck className="w-5 h-5" />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
