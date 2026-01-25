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

interface AxiomState {
    // Phase 4
    currentProject: Project | null;
    setCurrentProject: (project: Project | null) => void;

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
    currentProject: { id: 'proj-123', name: 'Demo Project', security_context: 'public' }, // Mock default project
};

export const useAxiomStore = create<AxiomState>((set) => ({
    ...initialState,

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

    reset: () => set(initialState),
}));
