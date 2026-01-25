'use client';

import { useLearnerStore } from '@/store/learner';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ProgressiveDisclosureProps {
    title: string;
    children: React.ReactNode;
    initiallyExpanded?: boolean;
    requiredLevel?: 'beginner' | 'intermediate' | 'expert';
}

export function ProgressiveDisclosure({
    title,
    children,
    initiallyExpanded = false,
    requiredLevel = 'intermediate'
}: ProgressiveDisclosureProps) {
    const { globalLevel, showAdvancedControls } = useLearnerStore();
    const [isExpanded, setIsExpanded] = useState(initiallyExpanded);

    const levels = ['beginner', 'intermediate', 'expert'];
    const userLevelIdx = levels.indexOf(globalLevel);
    const reqIdx = levels.indexOf(requiredLevel);

    // If user is below required level, hide entirely unless they enabled advanced controls specifically
    if (userLevelIdx < reqIdx && !showAdvancedControls) {
        return null;
    }

    return (
        <div className="border border-white/5 rounded-lg overflow-hidden bg-black/10">
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-3 text-sm text-gray-400 hover:bg-white/5 transition-colors"
            >
                <span className="font-medium">{title}</span>
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="p-3 border-t border-white/5"
                    >
                        {children}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
