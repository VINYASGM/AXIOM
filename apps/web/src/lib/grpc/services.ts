/**
 * AXIOM Service Clients
 * 
 * Typed clients for each AXIOM gRPC service.
 * Uses the base GrpcClient with service-specific types.
 */

import { GrpcClient, getGrpcClient, StreamOptions } from './client';

// ============================================================================
// GENERATION SERVICE TYPES
// ============================================================================

export interface GenerateRequest {
    raw_intent: string;
    language?: string;
    model_id?: string;
    contracts?: Contract[];
    options?: GenerationOptions;
}

export interface Contract {
    type: string;
    expression: string;
    description?: string;
}

export interface GenerationOptions {
    max_candidates?: number;
    timeout_seconds?: number;
    run_tier2_verification?: boolean;
    run_tier3_verification?: boolean;
    max_cost?: number;
}

export interface GenerationEvent {
    ivcu_id: string;
    timestamp: number;
    started?: GenerationStarted;
    token?: TokenGenerated;
    candidate?: CandidateComplete;
    verification?: VerificationProgress;
    complete?: GenerationComplete;
    error?: GenerationError;
    cost?: CostUpdate;
}

export interface GenerationStarted {
    model_id: string;
    model_name: string;
    tier: string;
    estimated_cost: number;
}

export interface TokenGenerated {
    candidate_id: string;
    token: string;
    token_index: number;
    is_complete: boolean;
}

export interface CandidateComplete {
    candidate_id: string;
    code: string;
    confidence: number;
    reasoning: string;
    tokens_used: number;
}

export interface VerificationProgress {
    candidate_id: string;
    tier: string;
    verifier: string;
    passed: boolean;
    confidence: number;
    errors: string[];
    warnings: string[];
    execution_time_ms: number;
}

export interface GenerationComplete {
    success: boolean;
    selected_candidate_id: string;
    final_code: string;
    overall_confidence: number;
    total_candidates: number;
    passing_candidates: number;
    total_cost: number;
    total_time_ms: number;
}

export interface GenerationError {
    error_code: string;
    message: string;
    recoverable: boolean;
    suggested_action: string;
}

export interface CostUpdate {
    current_cost: number;
    estimated_remaining: number;
    model_id: string;
    tokens_used: number;
}

// ============================================================================
// VERIFICATION SERVICE TYPES
// ============================================================================

export interface VerifyRequest {
    code: string;
    language?: string;
    candidate_id?: string;
    contracts?: Contract[];
    options?: VerificationOptions;
}

export interface VerificationOptions {
    run_tier0?: boolean;
    run_tier1?: boolean;
    run_tier2?: boolean;
    run_tier3?: boolean;
    timeout_seconds?: number;
    fail_fast?: boolean;
}

export interface QuickVerifyRequest {
    code: string;
    language?: string;
}

export interface QuickVerifyResponse {
    passed: boolean;
    confidence: number;
    parse_time_ms: number;
    errors: SyntaxError[];
    ast_info: ASTInfo;
}

export interface SyntaxError {
    line: number;
    column: number;
    end_line: number;
    end_column: number;
    message: string;
    severity: string;
}

export interface ASTInfo {
    root_type: string;
    node_count: number;
    functions: FunctionInfo[];
    classes: ClassInfo[];
    imports: string[];
}

export interface FunctionInfo {
    name: string;
    start_line: number;
    end_line: number;
}

export interface ClassInfo {
    name: string;
    start_line: number;
    end_line: number;
}

export interface VerificationEvent {
    ivcu_id: string;
    candidate_id: string;
    timestamp: number;
    tier_started?: TierStarted;
    tier_progress?: TierProgressEvent;
    tier_complete?: TierComplete;
    complete?: VerificationComplete;
    error?: VerificationError;
}

export interface TierStarted {
    tier: string;
    description: string;
    verifier_count: number;
}

export interface TierProgressEvent {
    tier: string;
    verifier: string;
    status: string;
    progress_percent: number;
}

export interface TierComplete {
    tier: string;
    passed: boolean;
    confidence: number;
    execution_time_ms: number;
    results: VerifierResult[];
}

export interface VerifierResult {
    verifier: string;
    passed: boolean;
    confidence: number;
    errors: string[];
    warnings: string[];
    details: Record<string, string>;
}

export interface VerificationComplete {
    candidate_id: string;
    passed: boolean;
    confidence: number;
    total_time_ms: number;
    tier0?: TierSummary;
    tier1?: TierSummary;
    tier2?: TierSummary;
    tier3?: TierSummary;
}

export interface TierSummary {
    ran: boolean;
    passed: boolean;
    confidence: number;
    error_count: number;
    warning_count: number;
}

export interface VerificationError {
    error_code: string;
    message: string;
    tier: string;
    verifier: string;
}

// ============================================================================
// MEMORY SERVICE TYPES
// ============================================================================

export interface SearchRequest {
    query: string;
    project_id?: string;
    tier?: number;
    node_types?: string[];
    limit?: number;
    similarity_threshold?: number;
    include_related?: boolean;
    max_depth?: number;
}

export interface SearchResponse {
    primary_nodes: MemoryNode[];
    related_nodes: MemoryNode[];
    relationships: MemoryEdge[];
    query_time_ms: number;
    best_score: number;
}

export interface MemoryNode {
    id: string;
    content: string;
    node_type: string;
    tier: number;
    metadata: Record<string, string>;
    created_at: string;
    source_ivcu_id?: string;
    project_id?: string;
    similarity_score?: number;
}

export interface MemoryEdge {
    id: string;
    source_id: string;
    target_id: string;
    relationship: number;
    weight: number;
    metadata: Record<string, string>;
}

export interface StoreRequest {
    content: string;
    node_type: string;
    tier?: number;
    metadata?: Record<string, string>;
    source_ivcu_id?: string;
    project_id?: string;
    relationships?: Relationship[];
}

export interface Relationship {
    target_id: string;
    type: number;
}

export interface StoreResponse {
    node_id: string;
    success: boolean;
}

export interface ImpactRequest {
    node_id: string;
    max_depth?: number;
}

export interface ImpactResponse {
    source_node_id: string;
    affected_count: number;
    impact_severity: string;
    max_depth_reached: number;
    affected_nodes: AffectedNode[];
}

export interface AffectedNode {
    id: string;
    content_preview: string;
    node_type: string;
    depth: number;
    relationship: string;
}

// ============================================================================
// GENERATION SERVICE CLIENT
// ============================================================================

export class GenerationService {
    constructor(private client: GrpcClient = getGrpcClient()) { }

    /**
     * Stream code generation with real-time tokens
     */
    async *generate(
        request: GenerateRequest,
        options?: StreamOptions
    ): AsyncGenerator<GenerationEvent> {
        yield* this.client.serverStream<GenerateRequest, GenerationEvent>(
            '/generation/stream',
            request,
            options
        );
    }

    /**
     * Simple unary generation (blocks until complete)
     */
    async generateSync(request: GenerateRequest): Promise<GenerationComplete> {
        const response = await this.client.unary<GenerateRequest, { result: GenerationComplete }>(
            '/generation/generate',
            request
        );
        return response.data.result;
    }

    /**
     * Get generation status
     */
    async getStatus(ivcuId: string): Promise<{
        ivcu_id: string;
        status: string;
        candidates_generated: number;
        candidates_verified: number;
        current_cost: number;
        elapsed_time_ms: number;
    }> {
        const response = await this.client.unary(
            '/generation/status',
            { ivcu_id: ivcuId }
        );
        return response.data as any;
    }

    /**
     * Cancel ongoing generation
     */
    async cancel(ivcuId: string, reason?: string): Promise<{ success: boolean; message: string }> {
        const response = await this.client.unary(
            '/generation/cancel',
            { ivcu_id: ivcuId, reason }
        );
        return response.data as any;
    }
}

// ============================================================================
// VERIFICATION SERVICE CLIENT
// ============================================================================

export class VerificationService {
    constructor(private client: GrpcClient = getGrpcClient()) { }

    /**
     * Stream verification progress
     */
    async *verify(
        request: VerifyRequest,
        options?: StreamOptions
    ): AsyncGenerator<VerificationEvent> {
        yield* this.client.serverStream<VerifyRequest, VerificationEvent>(
            '/verification/stream',
            request,
            options
        );
    }

    /**
     * Quick Tier 0 verification (synchronous, <10ms)
     */
    async quickVerify(code: string, language = 'python'): Promise<QuickVerifyResponse> {
        const response = await this.client.unary<QuickVerifyRequest, QuickVerifyResponse>(
            '/verification/quick',
            { code, language }
        );
        return response.data;
    }

    /**
     * Get cached verification result
     */
    async getResult(ivcuId: string, candidateId: string): Promise<VerificationComplete | null> {
        const response = await this.client.unary(
            '/verification/result',
            { ivcu_id: ivcuId, candidate_id: candidateId }
        );
        const data = response.data as any;
        return data.found ? data.result : null;
    }
}

// ============================================================================
// MEMORY SERVICE CLIENT
// ============================================================================

export class MemoryService {
    constructor(private client: GrpcClient = getGrpcClient()) { }

    /**
     * Search memory with GraphRAG
     */
    async search(request: SearchRequest): Promise<SearchResponse> {
        const response = await this.client.unary<SearchRequest, SearchResponse>(
            '/memory/search',
            request
        );
        return response.data;
    }

    /**
     * Stream search results as they're found
     */
    async *searchStream(
        request: SearchRequest,
        options?: StreamOptions
    ): AsyncGenerator<MemoryNode> {
        yield* this.client.serverStream<SearchRequest, MemoryNode>(
            '/memory/search/stream',
            request,
            options
        );
    }

    /**
     * Store a memory node
     */
    async store(request: StoreRequest): Promise<StoreResponse> {
        const response = await this.client.unary<StoreRequest, StoreResponse>(
            '/memory/store',
            request
        );
        return response.data;
    }

    /**
     * Get impact analysis
     */
    async getImpact(nodeId: string, maxDepth = 3): Promise<ImpactResponse> {
        const response = await this.client.unary<ImpactRequest, ImpactResponse>(
            '/memory/impact',
            { node_id: nodeId, max_depth: maxDepth }
        );
        return response.data;
    }

    /**
     * Add relationship between nodes
     */
    async addRelationship(
        sourceId: string,
        targetId: string,
        relationship: number,
        weight = 1.0
    ): Promise<{ edge_id: string; success: boolean }> {
        const response = await this.client.unary(
            '/memory/relationship',
            { source_id: sourceId, target_id: targetId, relationship, weight }
        );
        return response.data as any;
    }
}

// ============================================================================
// SINGLETON INSTANCES
// ============================================================================

let generationService: GenerationService | null = null;
let verificationService: VerificationService | null = null;
let memoryService: MemoryService | null = null;

export function getGenerationService(): GenerationService {
    if (!generationService) {
        generationService = new GenerationService();
    }
    return generationService;
}

export function getVerificationService(): VerificationService {
    if (!verificationService) {
        verificationService = new VerificationService();
    }
    return verificationService;
}

export function getMemoryService(): MemoryService {
    if (!memoryService) {
        memoryService = new MemoryService();
    }
    return memoryService;
}
