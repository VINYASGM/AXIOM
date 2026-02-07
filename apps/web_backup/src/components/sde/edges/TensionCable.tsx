'use client';

import { BaseEdge, EdgeProps, getBezierPath } from 'reactflow';
import { motion } from 'framer-motion';

export function TensionCable({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd, data }: EdgeProps) {
    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    });

    const status = data?.status || 'verified'; // verified | generating | failed

    // Status Logic
    const getColor = () => {
        if (status === 'verified') return '#10B981'; // Emerald
        if (status === 'failed') return '#EF4444';   // Red
        if (status === 'generating') return '#6366f1'; // Axiom Indigo
        return '#71717a'; // Zinc
    };

    const color = getColor();

    // Physics Animation Variants
    const pathVariants = {
        verified: {
            pathLength: 1,
            opacity: 1,
            transition: { duration: 0.8, ease: "circOut" },
            strokeDasharray: "0 0"
        },
        generating: {
            pathLength: [0, 1],
            opacity: [0.5, 1],
            transition: { duration: 1.5, repeat: Infinity, ease: "linear" },
            strokeDasharray: "4 4"
        },
        failed: {
            // "Vibrating" Effect
            d: [
                edgePath,
                edgePath.replace('C', `C ${sourceX + 2} ${sourceY + 2},`), // Micro jitter
                edgePath.replace('C', `C ${sourceX - 2} ${sourceY - 2},`)
            ],
            transition: { duration: 0.1, repeat: Infinity },
            strokeDasharray: "2 2"
        }
    };

    return (
        <>
            <motion.path
                id={id}
                d={edgePath}
                fill="none"
                stroke={color}
                strokeWidth={status === 'verified' ? 2 : 1.5}
                markerEnd={markerEnd}
                initial={{ pathLength: 0, opacity: 0 }}
                animate={status as any}
                variants={pathVariants as any}
                style={{
                    ...style,
                    filter: status === 'verified' ? `drop-shadow(0 0 3px ${color})` : 'none'
                }}
                className="react-flow__edge-path"
            />

            {/* Semantic Label */}
            {data?.label && (
                <foreignObject width={100} height={40} x={labelX - 50} y={labelY - 20} className="overflow-visible pointer-events-none">
                    <div className="flex justify-center items-center h-full">
                        <span className={`
                            px-1.5 py-0.5 rounded text-[10px] font-mono border backdrop-blur-sm
                            ${status === 'verified' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                                status === 'failed' ? 'bg-red-500/10 border-red-500/30 text-red-500' :
                                    'bg-black/40 border-white/10 text-gray-500'}
                         `}>
                            {data.label}
                        </span>
                    </div>
                </foreignObject>
            )}
        </>
    );
}
