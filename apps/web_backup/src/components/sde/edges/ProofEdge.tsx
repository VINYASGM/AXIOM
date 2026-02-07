'use client';

import { BaseEdge, EdgeProps, getBezierPath } from 'reactflow';

export function ProofEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd, data }: EdgeProps) {
    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    });

    const isVerified = data?.verified;
    const strokeColor = isVerified ? '#10B981' : '#EAB308'; // Emerald vs Amber
    const strokeDash = isVerified ? '0' : '5,5';

    return (
        <>
            <BaseEdge
                path={edgePath}
                markerEnd={markerEnd}
                style={{
                    ...style,
                    stroke: strokeColor,
                    strokeWidth: 2,
                    strokeDasharray: strokeDash,
                    filter: `drop-shadow(0 0 4px ${strokeColor}40)`
                }}
            />
            {data?.label && (
                <text x={labelX} y={labelY - 10} className="fill-gray-400 text-[10px] font-mono text-center pointer-events-none">
                    {data.label}
                </text>
            )}
        </>
    );
}
