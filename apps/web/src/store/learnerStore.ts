import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Define Skill Domain Enum
export enum SkillDomain {
    IntentExpression = "intent_expression",
    ContractReading = "contract_reading",
    VerificationInterpretation = "verification_interpretation",
    FailureDebugging = "debugging",
    ArchitecturalReasoning = "architectural_reasoning",
}

interface LearnerState {
    userId: string | null;
    globalLevel: 'novice' | 'intermediate' | 'expert';
    skills: Record<string, number>;
    lastUpdated: string | null;

    // Actions
    setProfile: (profile: any) => void;
    updateSkill: (domain: string, value: number) => void;
    recordEvent: (eventType: string, details?: any) => Promise<void>;
    fetchProfile: () => Promise<void>;
}

export const useLearnerStore = create<LearnerState>()(
    persist(
        (set, get) => ({
            userId: null,
            globalLevel: 'novice',
            skills: {},
            lastUpdated: null,

            setProfile: (profile) => set({
                userId: profile.UserId || profile.user_id,
                globalLevel: profile.GlobalLevel || profile.global_level || 'novice',
                skills: profile.Skills || profile.skills || {},
                lastUpdated: profile.LastUpdated || profile.updated_at
            }),

            updateSkill: (domain, value) => set((state) => ({
                skills: { ...state.skills, [domain]: value }
            })),

            fetchProfile: async () => {
                try {
                    const token = localStorage.getItem('axiom_token');
                    if (!token) return;

                    const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8080'}/api/v1/user/learner`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    if (res.ok) {
                        const data = await res.json();
                        get().setProfile(data);
                    }
                } catch (e) {
                    console.error("Failed to fetch learner profile", e);
                }
            },

            recordEvent: async (eventType, details = {}) => {
                try {
                    const token = localStorage.getItem('axiom_token');
                    if (!token) return;

                    // Optimistic update for UI responsiveness could go here

                    const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8080'}/api/v1/user/learner/event`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            event_type: eventType,
                            details
                        })
                    });

                    if (res.ok) {
                        // Re-fetch to get authoritative state from backend -> AI service
                        get().fetchProfile();
                    }
                } catch (e) {
                    console.error("Failed to record learning event", e);
                }
            }
        }),
        {
            name: 'axiom-learner-storage', // unique name
        }
    )
);
