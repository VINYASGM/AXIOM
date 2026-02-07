/**
 * Hooks Index
 * 
 * Export all AXIOM React hooks for streaming generation, verification, and memory.
 */

export { useGeneration } from './useGeneration';
export type {
    GenerationToken,
    CandidateResult,
    VerificationProgress,
    CostInfo,
    GenerationState,
    UseGenerationOptions,
    GenerationRequest
} from './useGeneration';

export { useGenerationWithGrpc } from './useGenerationWithGrpc';
export type {
    UseGenerationGrpcOptions,
    GenerationGrpcRequest
} from './useGenerationWithGrpc';

export { useVerification } from './useVerification';
export type {
    TierResult,
    VerificationError,
    VerificationWarning,
    SyntaxInfo,
    VerificationState,
    UseVerificationOptions
} from './useVerification';

export { useMemory } from './useMemory';
export type {
    MemoryTier,
    RelationshipType,
    MemoryNode,
    MemoryEdge,
    SearchResult,
    ImpactAnalysis,
    MemoryState,
    UseMemoryOptions
} from './useMemory';

export { useModelSelector } from './useModelSelector';
