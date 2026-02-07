'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { useSDEStore } from '@/store/sde';
import { Activity, ShieldCheck, ShieldAlert, Zap } from 'lucide-react';

type IntentNodeData = {
    label: string;
    description?: string;
    confidence: number;
    status: 'verified' | 'generating' | 'failed' | 'draft';
    constraints: string[];
    complexity: 'low' | 'medium' | 'high';
};

export const IntentManifold = memo(({ data, id, selected }: NodeProps<IntentNodeData>) => {
    const { isLensActive, setLensTarget } = useSDEStore();

    // Physics-based Interactions
    const x = useMotionValue(0);
    const y = useMotionValue(0);
    const rotateX = useTransform(y, [-100, 100], [30, -30]);
    const rotateY = useTransform(x, [-100, 100], [-30, 30]);

    // Spring physics for "Mass" feel
    const springConfig = { damping: 25, stiffness: 150 };
    const springX = useSpring(x, springConfig);
    const springY = useSpring(y, springConfig);

    const handleMouseMove = (e: React.MouseEvent) => {
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        x.set(e.clientX - centerX);
        y.set(e.clientY - centerY);
    };

    const handleMouseLeave = () => {
        x.set(0);
        y.set(0);
        setLensTarget(null);
    };

    // Semantic Visuals
    const getVisuals = () => {
        const base = data.status === 'verified' ? 'from-emerald-900/40 to-emerald-950/90' :
            data.status === 'failed' ? 'from-red-900/40 to-red-950/90' :
                data.status === 'generating' ? 'from-axiom-900/40 to-axiom-950/90' :
                    'from-zinc-900/40 to-zinc-950/90';

        const border = data.status === 'verified' ? 'border-emerald-500/30' :
            data.status === 'failed' ? 'border-red-500/30' :
                data.status === 'generating' ? 'border-axiom-500/30' :
                    'border-white/10';

        // Elevation (Z-Index / Shadow) based on Confidence
        const elevation = data.confidence > 0.9 ? 'shadow-[0_20px_50px_-12px_rgba(16,185,129,0.3)]' :
            data.confidence > 0.5 ? 'shadow-[0_10px_30px_-10px_rgba(245,158,11,0.2)]' :
                'shadow-[0_5px_15px_-5px_rgba(255,255,255,0.1)]';

        return { base, border, elevation };
    };

    const visuals = getVisuals();
    const isTargeted = isLensActive; // For simplified demo logic

    return (
        <motion.div
            style={{
                rotateX: selected ? rotateX : 0,
                rotateY: selected ? rotateY : 0,
                perspective: 1000
            }}
            className="relative group perspective-1000"
            onMouseMove={handleMouseMove}
            onMouseEnter={() => isLensActive && setLensTarget(id)}
            onMouseLeave={handleMouseLeave}
        >
            {/* The Manifold (Main Body) */}
            <motion.div
                className={`
                    w-96 rounded-2xl border backdrop-blur-md transition-all duration-300
                    bg-gradient-to-br ${visuals.base} ${visuals.border} ${visuals.elevation}
                    ${selected ? 'scale-[1.02] ring-1 ring-white/20' : ''}
                `}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
            >
                {/* Topographic Noise Texture */}
                <div className="absolute inset-0 opacity-10 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] rounded-2xl pointer-events-none" />

                {/* Header Layer */}
                <div className="relative p-5 border-b border-white/5 bg-white/5 rounded-t-2xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`
                            p-2 rounded-lg 
                            ${data.status === 'verified' ? 'bg-emerald-500/20 text-emerald-400' :
                                data.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-gray-800 text-gray-400'}
                         `}>
                            {data.status === 'verified' && <ShieldCheck className="w-5 h-5" />}
                            {data.status === 'failed' && <ShieldAlert className="w-5 h-5" />}
                            {data.status === 'generating' && <Activity className="w-5 h-5 animate-pulse" />}
                            {data.status === 'draft' && <Zap className="w-5 h-5" />}
                        </div>
                        <div>
                            <h3 className="font-bold text-gray-100 text-lg tracking-tight">{data.label}</h3>
                            <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] uppercase tracking-wider font-mono text-gray-500">
                                    Confidence: {(data.confidence * 100).toFixed(0)}%
                                </span>
                                {/* Semantic Height Indicator */}
                                <div className="h-1 w-16 bg-gray-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-current transition-all duration-1000"
                                        style={{ width: `${data.confidence * 100}%`, color: data.status === 'verified' ? '#10B981' : '#F59E0B' }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Content Layer */}
                <div className="relative p-5 space-y-4">
                    <p className="text-sm text-gray-400 font-normal leading-relaxed">
                        {data.description || "No description provided."}
                    </p>

                    {/* Constraint Anchors */}
                    {data.constraints && data.constraints.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                            {data.constraints.map((c, i) => (
                                <span
                                    key={i}
                                    className="px-2.5 py-1 text-[11px] font-mono rounded border border-white/5 bg-black/20 text-gray-300 flex items-center gap-1.5"
                                >
                                    <div className="w-1 h-1 rounded-full bg-axiom-400" />
                                    {c}
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Holographic Lens Response */}
                {isTargeted && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="absolute inset-0 bg-axiom-500/5 rounded-2xl border border-axiom-500/30 z-10 pointer-events-none"
                    />
                )}

            </motion.div>

            {/* Connection Handles */}
            <Handle type="target" position={Position.Left} className="!w-4 !h-4 !bg-white/10 !border-2 !border-white/20 !-left-2 transition-colors hover:!bg-axiom-500 hover:!border-axiom-300" />
            <Handle type="source" position={Position.Right} className="!w-4 !h-4 !bg-emerald-500/20 !border-2 !border-emerald-500 !-right-2 transition-colors hover:!bg-emerald-400" />
        </motion.div>
    );
});

IntentManifold.displayName = 'IntentManifold';
