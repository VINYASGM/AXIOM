/**
 * AXIOM gRPC Client Library
 * 
 * Exports the gRPC client and service clients for frontend use.
 */

// Core client
export {
    GrpcClient,
    BidiStream,
    GrpcError,
    getGrpcClient
} from './client';

export type {
    GrpcClientConfig,
    TransportType,
    StreamOptions,
    UnaryResponse
} from './client';

// Service clients
export {
    GenerationService,
    VerificationService,
    MemoryService,
    getGenerationService,
    getVerificationService,
    getMemoryService
} from './services';

// Generation types
export type {
    GenerateRequest,
    Contract,
    GenerationOptions,
    GenerationEvent,
    GenerationStarted,
    TokenGenerated,
    CandidateComplete,
    VerificationProgress,
    GenerationComplete,
    GenerationError,
    CostUpdate
} from './services';

// Verification types
export type {
    VerifyRequest,
    VerificationOptions,
    QuickVerifyRequest,
    QuickVerifyResponse,
    SyntaxError,
    ASTInfo,
    FunctionInfo,
    ClassInfo,
    VerificationEvent,
    TierStarted,
    TierProgressEvent,
    TierComplete,
    VerifierResult,
    VerificationComplete,
    TierSummary,
    VerificationError
} from './services';

// Memory types
export type {
    SearchRequest,
    SearchResponse,
    MemoryNode,
    MemoryEdge,
    StoreRequest,
    Relationship,
    StoreResponse,
    ImpactRequest,
    ImpactResponse,
    AffectedNode
} from './services';
