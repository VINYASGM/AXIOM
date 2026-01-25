'use client';

import { useLearnerStore } from '@/store/learner';
import { Lightbulb } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface AdaptiveHintProps {
    minLevel?: 'beginner' | 'intermediate' | 'expert';
    maxLevel?: 'beginner' | 'intermediate' | 'expert';
    children: React.ReactNode;
    className?: string;
}

export function AdaptiveHint({
    minLevel = 'beginner',
    maxLevel = 'intermediate',
    children,
    className = ""
}: AdaptiveHintProps) {
    const { globalLevel, showHints } = useLearnerStore();

    if (!showHints) return null;

    const levels = ['beginner', 'intermediate', 'expert'];
    const userLevelIdx = levels.indexOf(globalLevel);
    const minIdx = levels.indexOf(minLevel);
    const maxIdx = levels.indexOf(maxLevel);

    if (userLevelIdx < minIdx || userLevelIdx > maxIdx) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex gap-2 items-start text-xs text-amber-400/80 bg-amber-500/5 p-2 rounded-lg border border-amber-500/10 ${className}`}
            >
                <Lightbulb className="w-3 h-3 mt-0.5 shrink-0" />
                <div>{children}</div>
            </motion.div>
        </AnimatePresence>
    );
}
