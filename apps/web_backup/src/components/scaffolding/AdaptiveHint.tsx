'use client';

import { useAxiomStore } from '@/store/axiom';
import { Lightbulb } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface AdaptiveHintProps {
    minLevel?: 'novice' | 'intermediate' | 'expert';
    maxLevel?: 'novice' | 'intermediate' | 'expert';
    children: React.ReactNode;
    className?: string;
}

export function AdaptiveHint({
    minLevel = 'novice',
    maxLevel = 'intermediate',
    children,
    className = ""
}: AdaptiveHintProps) {
    const { learnerProfile } = useAxiomStore();

    // Default to novice if not loaded
    const currentLevel = learnerProfile?.global_level || 'novice';

    // Assuming we always show hints for now, or add a toggle in AxiomState later
    const showHints = true;

    if (!showHints) return null;

    const levels = ['novice', 'intermediate', 'expert'];
    const userLevelIdx = levels.indexOf(currentLevel);
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
