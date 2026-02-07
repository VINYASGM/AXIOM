import { create } from 'zustand';

export interface IVCU {
    id: string;
    rawIntent: string;
    parsedIntent: Record<string, unknown> | null;
    code: string | null;
    language: string;
    confidence: number;
    status: 'draft' | 'generating' | 'verifying' | 'verified' | 'failed' | 'deployed';
    contracts: Contract[];
    verificationResult: VerificationResult | null;
    retrievedContext?: RetrievedContext;
    candidates?: Candidate[];
    selectedCandidateId?: string;
    costUsd?: number;
}

export interface RetrievedContext {
    codeChunks: Array<{
        filePath: string;
        content: string;
        relevance?: number;
    }>;
    similarIntents: Array<{
        intent: string;
        score: number;
    }>;
}

export interface Candidate {
    id: string;
    code: string;
    confidence: number;
    verificationPassed: boolean;
    verificationScore: number;
    pruned: boolean;
}

export interface Contract {
    type: 'precondition' | 'postcondition' | 'invariant';
    description: string;
    expression?: string;
}

export interface VerificationResult {
    passed: boolean;
    confidence: number;
    period?: 'tier1' | 'tier2';
    verifierResults: VerifierResult[];
    limitations: string[];
    tier1Passed?: boolean;
    tier2Passed?: boolean;
    totalErrors?: number;
    totalWarnings?: number;
}

export interface VerifierResult {
    id?: string;
    name: string;
    tier: string;
    passed: boolean;
    confidence: number;
    messages: string[];
    errors?: string[];
    warnings?: string[];
    durationMs: number;
    details?: Record<string, any>;
}

export interface CostEstimate {
    estimatedCostUsd: number;
    inputTokens: number;
    outputTokens: number;
    embeddingTokens: number;
    model: string;
}

// Phase 4: Project & Team
export interface Project {
    id: string;
    name: string;
    security_context: string;
}

export interface LearnerProfile {
    user_id: string;
    global_level: 'novice' | 'intermediate' | 'expert';
    skills: Record<string, number>;
    last_updated: string;
}

interface AxiomState {
    // Phase 4
    currentProject: Project | null;

    // Current state
    currentIVCU: IVCU | null;
    isGenerating: boolean;

    // Auth
    token: string | null;

    // Intent input
    rawIntent: string;
    selectedLanguage: string;

    // Economics
    costEstimate: CostEstimate | null;
    budgetWarning: string | null;

    // Parsed result
    parsedIntent: Record<string, unknown> | null;
    parseConfidence: number;
    suggestedRefinements: string[];

    // Actions
    setRawIntent: (intent: string) => void;
    setSelectedLanguage: (language: string) => void;
    setParsedIntent: (parsed: Record<string, unknown>, confidence: number, refinements: string[]) => void;
    setCurrentIVCU: (ivcu: IVCU | null) => void;
    setIsGenerating: (generating: boolean) => void;
    setCostEstimate: (estimate: CostEstimate | null) => void;
    setBudgetWarning: (warning: string | null) => void;
    updateIVCUStatus: (status: IVCU['status']) => void;
    updateIVCUCode: (code: string, confidence: number) => void;
    setToken: (token: string | null) => void;
    setCurrentProject: (project: Project | null) => void;

    // Async Actions
    analyzeIntent: (intent: string) => Promise<void>;
    generateCode: () => Promise<void>;

    // Learner
    learnerProfile: LearnerProfile | null;
    fetchLearnerProfile: (token: string) => Promise<void>;

    reset: () => void;
}

const initialState = {
    currentIVCU: null,
    isGenerating: false,
    rawIntent: '',
    selectedLanguage: 'typescript',
    costEstimate: null,
    budgetWarning: null,
    parsedIntent: null,
    parseConfidence: 0,
    suggestedRefinements: [],
    token: null,
    currentProject: { id: '123e4567-e89b-12d3-a456-426614174000', name: 'Demo Project', security_context: 'public' }, // Mock default project
    learnerProfile: null,
};

export const useAxiomStore = create<AxiomState>((set, get) => ({
    ...initialState,

    analyzeIntent: async (intent: string) => {
        const { token, selectedLanguage } = get();
        // Allow analysis even without token for demo/local mode if backend allows, but spec says auth required.
        // For now, let's assume token might be null in dev.

        set({ rawIntent: intent });

        try {
            // Parallel: Parse Intent + Estimate Cost
            const headers: HeadersInit = token
                ? { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
                : { 'Content-Type': 'application/json' };

            const [parseRes, costRes] = await Promise.all([
                fetch('/api/v1/intent/parse', {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({ raw_intent: intent })
                }),
                fetch('/api/v1/cost/estimate', {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({ intent, language: selectedLanguage, candidate_count: 3 })
                })
            ]);

            if (parseRes.ok) {
                const data = await parseRes.json();
                set({
                    parsedIntent: data.parsed_intent,
                    parseConfidence: data.confidence,
                    suggestedRefinements: data.suggested_refinements
                });
            }

            if (costRes.ok) {
                const data = await costRes.json();
                set({
                    costEstimate: {
                        estimatedCostUsd: data.estimated_cost_usd,
                        inputTokens: data.input_tokens,
                        outputTokens: data.output_tokens,
                        embeddingTokens: data.embedding_tokens,
                        model: data.model
                    }
                });
            }
        } catch (e) {
            console.error("Analysis failed", e);
        }
    },

    generateCode: async () => {
        const { rawIntent, parsedIntent, selectedLanguage, token, currentProject } = get();
        set({ isGenerating: true });

        const headers: HeadersInit = token
            ? { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
            : { 'Content-Type': 'application/json' };

        try {
            // 1. Create SDO/Intent
            const createRes = await fetch('/api/v1/intent/create', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    project_id: currentProject?.id || 'default-project',
                    raw_intent: rawIntent,
                    contracts: []
                })
            });

            if (!createRes.ok) throw new Error('Failed to create intent');
            const { ivcu_id } = await createRes.json();

            // 2. Start Generation Strategy (Async)
            const startRes = await fetch('/api/v1/generation/start', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    ivcu_id,
                    language: selectedLanguage,
                    candidate_count: 3,
                    strategy: 'parallel'
                })
            });

            if (!startRes.ok) throw new Error('Failed to start generation');

            // 3. Set Initial IVCU State and start polling
            set({
                currentIVCU: {
                    id: ivcu_id,
                    rawIntent,
                    parsedIntent,
                    code: '# Generating...',
                    language: selectedLanguage,
                    confidence: 0,
                    status: 'generating',
                    contracts: [],
                    verificationResult: null
                }
            });

            // Poll for completion (Simple implementation for now)
            const poll = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/api/v1/generation/${ivcu_id}/status`, { headers });
                    if (statusRes.ok) {
                        const status = await statusRes.json();
                        if (status.status === 'verified' || status.status === 'failed') {
                            clearInterval(poll);

                            // Fetch full result
                            const resultRes = await fetch(`/api/v1/intent/${ivcu_id}`, { headers });
                            if (resultRes.ok) {
                                const ivcuData = await resultRes.json();
                                set({
                                    currentIVCU: {
                                        id: ivcuData.id,
                                        rawIntent: ivcuData.raw_intent,
                                        parsedIntent: ivcuData.parsed_intent,
                                        code: ivcuData.code,
                                        language: ivcuData.language,
                                        confidence: ivcuData.confidence_score,
                                        status: ivcuData.status,
                                        contracts: ivcuData.contracts || [],
                                        verificationResult: ivcuData.verification_result,
                                        costUsd: 0
                                    },
                                    isGenerating: false
                                });
                            }
                        }
                    }
                } catch (e) {
                    // console.error("Poll failed", e);
                }
            }, 1000);

            // Safety timeout
            setTimeout(() => { clearInterval(poll); set(s => ({ isGenerating: false })); }, 60000);

        } catch (e) {
            console.error("Generation failed", e);
            set({ isGenerating: false });
        }
    },

    setRawIntent: (intent) => set({ rawIntent: intent }),

    setSelectedLanguage: (language) => set({ selectedLanguage: language }),

    setParsedIntent: (parsed, confidence, refinements) => set({
        parsedIntent: parsed,
        parseConfidence: confidence,
        suggestedRefinements: refinements,
    }),

    setCurrentIVCU: (ivcu) => set({ currentIVCU: ivcu }),

    setIsGenerating: (generating) => set({ isGenerating: generating }),

    setCostEstimate: (estimate) => set({ costEstimate: estimate }),

    setBudgetWarning: (warning) => set({ budgetWarning: warning }),

    updateIVCUStatus: (status) => set((state) => ({
        currentIVCU: state.currentIVCU
            ? { ...state.currentIVCU, status }
            : null,
    })),

    updateIVCUCode: (code, confidence) => set((state) => ({
        currentIVCU: state.currentIVCU
            ? { ...state.currentIVCU, code, confidence, status: 'verified' }
            : null,
    })),

    setToken: (token) => set({ token }),

    setCurrentProject: (project: Project | null) => set({ currentProject: project }),

    // Learner Model
    learnerProfile: null,
    fetchLearnerProfile: async (token: string) => {
        try {
            const res = await fetch('/api/v1/user/learner', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                set({ learnerProfile: data });
            }
        } catch (err) {
            console.error("Failed to fetch learner profile", err);
        }
    },

    reset: () => set(initialState),
}));
