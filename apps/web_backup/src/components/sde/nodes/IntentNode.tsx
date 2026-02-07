'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, Shield, Activity, GitBranch } from 'lucide-react';
import { useSDEStore } from '@/store/sde';

type IntentNodeData = {
    label: string;
    description?: string;
    confidence: number;
    status: 'verified' | 'generating' | 'failed' | 'draft';
    constraints: string[];
};

export const IntentNode = memo(({ data, id, selected }: NodeProps<IntentNodeData>) => {
    const { isLensActive, lensTargetId, setLensTarget } = useSDEStore();
    const isTargeted = lensTargetId === id;

    // Status Colors
    const getColors = () => {
        switch (data.status) {
            case 'verified': return { border: 'border-emerald-500', bg: 'bg-emerald-500/10', glow: 'shadow-emerald-500/20' };
            case 'failed': return { border: 'border-red-500', bg: 'bg-red-500/10', glow: 'shadow-red-500/20' };
            case 'generating': return { border: 'border-axiom-500', bg: 'bg-axiom-500/10', glow: 'shadow-axiom-500/20' };
            default: return { border: 'border-white/20', bg: 'bg-white/5', glow: 'shadow-none' };
        }
    };
    const colors = getColors();

    // Confidence Opacity
    const opacity = Math.max(0.4, data.confidence);

    return (
        <motion.div
            className={`
                relative w-80 rounded-xl border-2 backdrop-blur-xl transition-all duration-300 group
                ${colors.border} ${colors.bg} ${selected ? 'ring-2 ring-white/50 scale-[1.02]' : ''}
                ${isTargeted ? 'opacity-20 blur-[2px]' : ''} 
                shadow-lg ${colors.glow}
            `}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            onMouseEnter={() => isLensActive && setLensTarget(id)}
            onMouseLeave={() => setLensTarget(null)}
        >
            {/* Input Handle */}
            <Handle type="target" position={Position.Left} className="w-3 h-3 bg-white/50 !border-none" />

            {/* Header */}
            <div className="p-3 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {data.status === 'verified' && <ShieldCheck className="w-4 h-4 text-emerald-400" />}
                    {data.status === 'failed' && <ShieldAlert className="w-4 h-4 text-red-400" />}
                    {data.status === 'generating' && <Activity className="w-4 h-4 text-axiom-400 animate-pulse" />}
                    {data.status === 'draft' && <Shield className="w-4 h-4 text-gray-400" />}
                    <span className="font-semibold text-sm text-gray-200">{data.label}</span>
                </div>
                <div className="text-[10px] font-mono text-gray-500">
                    {(data.confidence * 100).toFixed(0)}%
                </div>
            </div>

            {/* Body */}
            <div className="p-3 space-y-2">
                <p className="text-xs text-gray-400 italic font-mono leading-relaxed">
                    {data.description || "No description provided."}
                </p>

                {/* Constraints */}
                {data.constraints && data.constraints.length > 0 && (
                    <div className="space-y-1 mt-2">
                        {data.constraints.map((c, i) => (
                            <div key={i} className="flex items-center gap-1.5 text-[10px] text-gray-300 bg-black/20 px-2 py-1 rounded">
                                <GitBranch className="w-3 h-3 text-white/30" />
                                {c}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Output Handle */}
            <Handle type="source" position={Position.Right} className="w-3 h-3 bg-emerald-500 !border-none" />
        </motion.div>
    );
});

IntentNode.displayName = 'IntentNode';
