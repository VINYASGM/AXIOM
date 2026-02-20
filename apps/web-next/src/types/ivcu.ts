export interface ImplementationPlanDecision {
    decision: string;
    rationale: string;
    tradeoffs?: string | null;
}

export interface ImplementationPlan {
    summary: string;
    steps: string[];
    architecture: string[];
    key_decisions: ImplementationPlanDecision[];
    edge_cases: string[];
    estimated_effort?: { complexity: 'low' | 'medium' | 'high'; hours?: number } | null;
}

export interface IVCU {
    id: string;
    rawIntent: string;
    parsedIntent: Record<string, unknown> | null;
    code: string | null;
    language: string;
    confidence: number;
    status: 'draft' | 'generating' | 'verifying' | 'verified' | 'failed' | 'deployed';
    contracts: any[];
    verificationResult: any | null;
    implementation_plan?: ImplementationPlan | null;
}
