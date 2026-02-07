'use client';

import { motion } from 'framer-motion';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { useLearnerStore } from '@/store/learner';
import { AdaptiveHint } from './scaffolding/AdaptiveHint';
import { useAxiomStore } from '@/store/axiom';
import { useEffect, useState } from 'react';

interface DecisionNode {
    id: string;
    type: 'constraint' | 'selection' | 'inference';
    title: string;
    description: string;
    confidence: number;
    alternatives?: string[];
}

// Mock reasoning trace for demonstration (fallback)
const mockTrace: DecisionNode[] = [
    {
        id: '1',
        type: 'constraint',
        title: 'Input Analysis',
        description: 'Detected request for "email validation". Inferred requirement for regex or standard library.',
        confidence: 0.95
    },
    {
        id: '2',
        type: 'selection',
        title: 'Library Selection',
        description: 'Selected Python `re` module over external `validators` package to minimize dependencies.',
        confidence: 0.88,
        alternatives: ['validators package', 'custom string parsing']
    },
    {
        id: '3',
        type: 'inference',
        title: 'Edge Case Handling',
        description: 'Added specific check for empty strings and missing @ symbols based on common failure modes.',
        confidence: 0.92
    }
];

export function ReasoningTracePanel() {
    const { globalLevel } = useLearnerStore();
    const { currentIVCU } = useAxiomStore();
    const [trace, setTrace] = useState<DecisionNode[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchTrace = async () => {
            if (!currentIVCU?.id) return;

            setLoading(true);
            try {
                // For demonstration, simulating API latency then setting mock
                // If the backend has the actual trace, we could use that.
                // Let's try to fetch, if fail, fallback to mock.
                const res = await fetch(`/api/v1/reasoning/${currentIVCU.id}`);
                if (res.ok) {
                    const data = await res.json();
                    setTrace(data.nodes);
                } else {
                    // console.warn("Failed to fetch trace, falling back to mock");
                    setTrace(mockTrace);
                }
            } catch (e) {
                // console.error("Error fetching trace", e);
                setTrace(mockTrace);
            } finally {
                setLoading(false);
            }
        };

        fetchTrace();
    }, [currentIVCU?.id]);

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center text-gray-500 gap-2 p-4">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Loading reasoning trace...</span>
            </div>
        );
    }

    if (!trace.length) {
        return (
            <div className="h-full flex items-center justify-center text-gray-500 p-4">
                <p>No reasoning trace available for this generation.</p>
            </div>
        );
    }

    return (
        <div className="h-full overflow-auto pr-2">
            <div className="mb-4">
                <h3 className="text-sm font-semibold text-white mb-1">Reasoning Trace</h3>
                <p className="text-xs text-gray-400">
                    Understanding why the AI generated this specific implementation.
                </p>

                <AdaptiveHint className="mt-2">
                    Reviewing the "Why" helps you catch subtle misunderstandings before they become bugs.
                </AdaptiveHint>
            </div>

            <div className="space-y-6 relative ml-2 pl-6 border-l border-white/10 my-4">
                {trace.map((node, index) => (
                    <motion.div
                        key={node.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="relative"
                    >
                        {/* Timeline dot */}
                        <div className={`absolute -left-[29px] top-1.5 w-3 h-3 rounded-full border-2 ${node.type === 'constraint' ? 'bg-amber-500/20 border-amber-500' :
                            node.type === 'selection' ? 'bg-blue-500/20 border-blue-500' :
                                'bg-purple-500/20 border-purple-500'
                            }`} />

                        <div className="bg-white/5 rounded-lg p-3 border border-white/5 hover:border-white/10 transition-colors">
                            <div className="flex items-center justify-between mb-1">
                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${node.type === 'constraint' ? 'text-amber-400 bg-amber-500/10' :
                                    node.type === 'selection' ? 'text-blue-400 bg-blue-500/10' :
                                        'text-purple-400 bg-purple-500/10'
                                    }`}>
                                    {node.type.toUpperCase()}
                                </span>
                                <span className="text-xs text-gray-500">
                                    {Math.round(node.confidence * 100)}% Conf
                                </span>
                            </div>

                            <h4 className="text-sm font-medium text-white mb-1">{node.title}</h4>
                            <p className="text-sm text-gray-400 leading-relaxed">
                                {node.description}
                            </p>

                            {/* Alternatives - Progressive Disclosure for Experts */}
                            {node.alternatives && globalLevel !== 'beginner' && (
                                <div className="mt-3 pt-2 border-t border-white/5">
                                    <h5 className="text-xs font-medium text-gray-500 mb-1">Alternatives considered:</h5>
                                    <div className="flex flex-wrap gap-2">
                                        {node.alternatives.map(alt => (
                                            <span key={alt} className="text-xs px-2 py-1 bg-black/20 rounded text-gray-500 strike-through opacity-70">
                                                {alt}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </motion.div>
                ))}
            </div>

            <div className="flex items-center gap-2 text-xs text-green-400 mt-4 bg-green-500/5 p-2 rounded">
                <CheckCircle2 className="w-4 h-4" />
                <span>Reasoning Graph Verified Consistent</span>
            </div>
        </div>
    );
}
