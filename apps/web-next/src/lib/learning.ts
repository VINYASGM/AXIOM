export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';

export type LearningEvent =
    | 'BASIC_INTENT'
    | 'MULTI_STEP_FLOW'
    | 'STATEFUL_LOGIC'
    | 'ARCHITECTURAL_COMPOSITION'
    | 'HIGH_COMPLEXITY_SYSTEM';

export const adaptiveUIConfig: Record<SkillLevel, { showHints: boolean; showExamples: boolean; layout: 'guided' | 'standard' | 'compact' | 'raw' }> = {
    beginner: { showHints: true, showExamples: true, layout: 'guided' },
    intermediate: { showHints: true, showExamples: false, layout: 'standard' },
    advanced: { showHints: false, showExamples: false, layout: 'compact' },
    expert: { showHints: false, showExamples: false, layout: 'raw' },
};

export function detectArchitecturalComplexity(intent: any): LearningEvent {
    // heuristic - safe defaults; adjust keys to match your Intent shape
    const components = intent?.components?.length || 0;
    // If intent structure is flat, maybe we count distinct actions? 
    // For now assuming 'steps' or 'actions' array if components isn't the main structure.
    const steps = intent?.steps?.length || intent?.actions?.length || 0;

    const hasState = !!intent?.hasState || !!intent?.state;
    const hasAPIs = ('dataSources' in (intent || {})) || ('apis' in (intent || {})) || !!intent?.hasAPIs;
    const usesEventBus = !!intent?.usesEventBus || !!intent?.events;

    if (components > 5 && hasState && hasAPIs && (usesEventBus || steps > 4)) return 'HIGH_COMPLEXITY_SYSTEM';
    if (components > 3 && (hasState || hasAPIs)) return 'ARCHITECTURAL_COMPOSITION';
    if (steps > 3) return 'MULTI_STEP_FLOW';
    if (hasState) return 'STATEFUL_LOGIC';
    return 'BASIC_INTENT';
}

export function emitLearningEvent(payload: { type: LearningEvent; skillLevel: SkillLevel; intentId?: string; timestamp?: number }) {
    // Minimal emitter: call any existing analytics / event bus instead of console in production
    if (typeof window !== 'undefined' && (window as any).appEventBus) {
        (window as any).appEventBus.emit('learning:event', payload);
        return;
    }
    // Fallback for dev/debug
    if (process.env.NODE_ENV === 'development') {
        console.debug('learning:event', payload);
    }
}
