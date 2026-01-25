import { create } from 'zustand';

export type SkillLevel = 'beginner' | 'intermediate' | 'expert';

interface UserSkills {
    intentExpression: number; // 0-10
    verificationInterpretation: number; // 0-10
    architecturalReasoning: number; // 0-10
}

interface LearnerState {
    // Current user's global skill level (derived or set)
    globalLevel: SkillLevel;

    // Granular skills
    skills: UserSkills;

    // UI Preferences
    showHints: boolean;
    showAdvancedControls: boolean;

    // Actions
    setGlobalLevel: (level: SkillLevel) => void;
    updateSkill: (skill: keyof UserSkills, value: number) => void;
    toggleHints: () => void;
    fetchLearnerProfile: () => Promise<void>;
    reset: () => void;
}

const defaultSkills: UserSkills = {
    intentExpression: 3,
    verificationInterpretation: 2,
    architecturalReasoning: 1
};

export const useLearnerStore = create<LearnerState>((set) => ({
    globalLevel: 'beginner',
    skills: defaultSkills,
    showHints: true,
    showAdvancedControls: false,

    setGlobalLevel: (level) => set((state) => {
        // Auto-adjust UI flags based on level
        switch (level) {
            case 'beginner':
                return {
                    globalLevel: level,
                    showHints: true,
                    showAdvancedControls: false,
                    skills: { intentExpression: 3, verificationInterpretation: 2, architecturalReasoning: 1 }
                };
            case 'intermediate':
                return {
                    globalLevel: level,
                    showHints: true,
                    showAdvancedControls: true,
                    skills: { intentExpression: 6, verificationInterpretation: 6, architecturalReasoning: 4 }
                };
            case 'expert':
                return {
                    globalLevel: level,
                    showHints: false,
                    showAdvancedControls: true,
                    skills: { intentExpression: 9, verificationInterpretation: 9, architecturalReasoning: 9 }
                };
            default:
                return state;
        }
    }),

    updateSkill: (skill, value) => set((state) => ({
        skills: { ...state.skills, [skill]: value }
    })),

    toggleHints: () => set((state) => ({ showHints: !state.showHints })),

    fetchLearnerProfile: async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/user/learner`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (res.ok) {
                const data = await res.json();
                // Map API response to store state
                set((state) => {
                    // Assuming API returns { globalLevel, skills: {...} } matching store
                    // If simple match:
                    // return { globalLevel: data.globalLevel, skills: data.skills };

                    // Logic to update flags based on level:
                    const newState = { ...state, globalLevel: data.globalLevel, skills: data.skills };

                    // Re-run the level switch logic to set flags
                    switch (data.globalLevel) {
                        case 'beginner':
                            newState.showHints = true;
                            newState.showAdvancedControls = false;
                            break;
                        case 'intermediate':
                            newState.showHints = true;
                            newState.showAdvancedControls = true;
                            break;
                        case 'expert':
                            newState.showHints = false;
                            newState.showAdvancedControls = true;
                            break;
                    }
                    return newState;
                });
            }
        } catch (e) {
            console.error("Failed to fetch learner profile", e);
        }
    },

    reset: () => set({
        globalLevel: 'beginner',
        skills: defaultSkills,
        showHints: true,
        showAdvancedControls: false
    }),
}));
