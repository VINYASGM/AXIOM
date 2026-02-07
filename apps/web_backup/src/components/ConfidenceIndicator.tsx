'use client';

import { motion } from 'framer-motion';
import { Shield, AlertTriangle, CheckCircle2, Zap } from 'lucide-react';

interface ConfidenceIndicatorProps {
    confidence: number;
    size?: 'sm' | 'md' | 'lg';
    showLabel?: boolean;
}

export function ConfidenceIndicator({
    confidence,
    size = 'md',
    showLabel = true
}: ConfidenceIndicatorProps) {
    const getConfidenceLevel = () => {
        if (confidence >= 0.9) return { level: 'verified', color: 'cyan', icon: Zap };
        if (confidence >= 0.7) return { level: 'high', color: 'green', icon: CheckCircle2 };
        if (confidence >= 0.4) return { level: 'medium', color: 'amber', icon: Shield };
        return { level: 'low', color: 'red', icon: AlertTriangle };
    };

    const { level, color, icon: Icon } = getConfidenceLevel();
    const percentage = Math.round(confidence * 100);

    const sizes = {
        sm: { container: 'h-6', icon: 'w-3 h-3', text: 'text-xs' },
        md: { container: 'h-8', icon: 'w-4 h-4', text: 'text-sm' },
        lg: { container: 'h-10', icon: 'w-5 h-5', text: 'text-base' },
    };

    const colors: Record<string, { bg: string; border: string; text: string; fill: string }> = {
        cyan: {
            bg: 'bg-cyan-500/20',
            border: 'border-cyan-500/50',
            text: 'text-cyan-400',
            fill: 'bg-cyan-500',
        },
        green: {
            bg: 'bg-green-500/20',
            border: 'border-green-500/50',
            text: 'text-green-400',
            fill: 'bg-green-500',
        },
        amber: {
            bg: 'bg-amber-500/20',
            border: 'border-amber-500/50',
            text: 'text-amber-400',
            fill: 'bg-amber-500',
        },
        red: {
            bg: 'bg-red-500/20',
            border: 'border-red-500/50',
            text: 'text-red-400',
            fill: 'bg-red-500',
        },
    };

    const currentSize = sizes[size];
    const currentColor = colors[color];

    return (
        <div
            className={`inline-flex items-center gap-2 px-3 rounded-full border ${currentColor.bg} ${currentColor.border} ${currentSize.container}`}
        >
            <Icon className={`${currentSize.icon} ${currentColor.text}`} />

            {showLabel && (
                <div className="flex items-center gap-2">
                    <span className={`${currentSize.text} font-medium ${currentColor.text}`}>
                        {percentage}%
                    </span>

                    {/* Mini progress bar */}
                    <div className="w-12 h-1.5 bg-black/30 rounded-full overflow-hidden">
                        <motion.div
                            className={`h-full ${currentColor.fill} rounded-full`}
                            initial={{ width: 0 }}
                            animate={{ width: `${percentage}%` }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
