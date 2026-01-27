/**
 * useGenerationWithGrpc - React hook using gRPC service client
 * 
 * Alternative implementation using the gRPC service client library.
 * Provides the same interface as useGeneration but uses typed service clients.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import {
    GenerationService,
    getGenerationService,
    GenerationEvent as GrpcGenerationEvent
} from '../lib/grpc';

// Re-export types for convenience
export type { GenerationToken, CandidateResult, VerificationProgress, CostInfo } from './useGeneration';
import type { GenerationToken, CandidateResult, VerificationProgress, CostInfo, GenerationState } from './useGeneration';

export interface UseGenerationGrpcOptions {
    /** Optional custom GenerationService instance */
    service?: GenerationService;
    /** Called on each token */
    onToken?: (token: GenerationToken) => void;
    /** Called when candidate is complete */
    onCandidate?: (candidate: CandidateResult) => void;
    /** Called on verification progress */
    onVerification?: (progress: VerificationProgress) => void;
    /** Called when generation completes */
    onComplete?: (code: string, confidence: number) => void;
    /** Called on error */
    onError?: (error: string) => void;
}

export interface GenerationGrpcRequest {
    intent: string;
    language?: string;
    modelId?: string;
    contracts?: Array<{
        type: string;
        expression: string;
        description?: string;
    }>;
    options?: {
        maxCandidates?: number;
        timeoutSeconds?: number;
        runTier2?: boolean;
        runTier3?: boolean;
        maxCost?: number;
    };
}

/**
 * React hook for code generation using gRPC service client
 */
export function useGenerationWithGrpc(options: UseGenerationGrpcOptions = {}) {
    const {
        service = getGenerationService(),
        onToken,
        onCandidate,
        onVerification,
        onComplete,
        onError,
    } = options;

    // State
    const [state, setState] = useState<GenerationState>({
        status: 'idle',
        ivcuId: null,
        modelId: null,
        modelName: null,
        currentTokens: '',
        tokenCount: 0,
        candidates: new Map(),
        selectedCandidateId: null,
        finalCode: null,
        verificationProgress: [],
        cost: null,
        startTime: null,
        endTime: null,
        error: null,
    });

    // Abort controller for cancellation
    const abortControllerRef = useRef<AbortController | null>(null);

    /**
     * Generate code with streaming
     */
    const generate = useCallback(async (request: GenerationGrpcRequest) => {
        // Cancel any existing generation
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();

        // Reset state
        setState(prev => ({
            ...prev,
            status: 'generating',
            ivcuId: null,
            currentTokens: '',
            tokenCount: 0,
            candidates: new Map(),
            selectedCandidateId: null,
            finalCode: null,
            verificationProgress: [],
            cost: null,
            startTime: Date.now(),
            endTime: null,
            error: null,
        }));

        try {
            // Use the gRPC service client
            const stream = service.generate(
                {
                    raw_intent: request.intent,
                    language: request.language || 'python',
                    model_id: request.modelId,
                    contracts: request.contracts?.map(c => ({
                        type: c.type,
                        expression: c.expression,
                        description: c.description,
                    })),
                    options: request.options ? {
                        max_candidates: request.options.maxCandidates,
                        timeout_seconds: request.options.timeoutSeconds,
                        run_tier2_verification: request.options.runTier2,
                        run_tier3_verification: request.options.runTier3,
                        max_cost: request.options.maxCost,
                    } : undefined,
                },
                {
                    signal: abortControllerRef.current.signal,
                    onData: (event) => handleEvent(event),
                    onError: (error) => {
                        setState(prev => ({
                            ...prev,
                            status: 'error',
                            error: error.message,
                            endTime: Date.now(),
                        }));
                        onError?.(error.message);
                    },
                    onComplete: () => {
                        // Stream ended - check if we have a complete state
                        setState(prev => {
                            if (prev.status === 'generating' || prev.status === 'verifying') {
                                return { ...prev, endTime: Date.now() };
                            }
                            return prev;
                        });
                    },
                }
            );

            // Consume the stream
            for await (const event of stream) {
                handleEvent(event);
            }

        } catch (error: any) {
            if (error.name === 'AbortError') {
                setState(prev => ({ ...prev, status: 'cancelled', endTime: Date.now() }));
            } else {
                const errorMsg = error.message || 'Generation failed';
                setState(prev => ({
                    ...prev,
                    status: 'error',
                    error: errorMsg,
                    endTime: Date.now(),
                }));
                onError?.(errorMsg);
            }
        }
    }, [service, onError]);

    /**
     * Handle generation events from the stream
     */
    const handleEvent = useCallback((event: GrpcGenerationEvent) => {
        const ivcuId = event.ivcu_id;

        // Generation started
        if (event.started) {
            setState(prev => ({
                ...prev,
                ivcuId,
                modelId: event.started!.model_id,
                modelName: event.started!.model_name,
            }));
        }

        // Token generated
        if (event.token) {
            const token: GenerationToken = {
                candidateId: event.token.candidate_id,
                token: event.token.token,
                tokenIndex: event.token.token_index,
                isComplete: event.token.is_complete,
            };

            setState(prev => ({
                ...prev,
                currentTokens: prev.currentTokens + token.token,
                tokenCount: token.tokenIndex + 1,
            }));

            onToken?.(token);
        }

        // Candidate complete
        if (event.candidate) {
            const candidate: CandidateResult = {
                id: event.candidate.candidate_id,
                code: event.candidate.code,
                confidence: event.candidate.confidence,
                reasoning: event.candidate.reasoning,
                tokensUsed: event.candidate.tokens_used,
            };

            setState(prev => {
                const newCandidates = new Map(prev.candidates);
                newCandidates.set(candidate.id, candidate);
                return { ...prev, candidates: newCandidates };
            });

            onCandidate?.(candidate);
        }

        // Verification progress
        if (event.verification) {
            const progress: VerificationProgress = {
                candidateId: event.verification.candidate_id,
                tier: event.verification.tier as VerificationProgress['tier'],
                verifier: event.verification.verifier,
                passed: event.verification.passed,
                confidence: event.verification.confidence,
                errors: event.verification.errors || [],
                warnings: event.verification.warnings || [],
                executionTimeMs: event.verification.execution_time_ms,
            };

            setState(prev => ({
                ...prev,
                status: 'verifying',
                verificationProgress: [...prev.verificationProgress, progress],
            }));

            // Update candidate verification status
            setState(prev => {
                const newCandidates = new Map(prev.candidates);
                const candidate = newCandidates.get(progress.candidateId);
                if (candidate) {
                    newCandidates.set(progress.candidateId, {
                        ...candidate,
                        verificationPassed: progress.passed,
                        verificationTier: progress.tier,
                    });
                }
                return { ...prev, candidates: newCandidates };
            });

            onVerification?.(progress);
        }

        // Cost update
        if (event.cost) {
            setState(prev => ({
                ...prev,
                cost: {
                    currentCost: event.cost!.current_cost,
                    estimatedRemaining: event.cost!.estimated_remaining,
                    modelId: event.cost!.model_id,
                    tokensUsed: event.cost!.tokens_used,
                },
            }));
        }

        // Generation complete
        if (event.complete) {
            setState(prev => ({
                ...prev,
                status: 'complete',
                selectedCandidateId: event.complete!.selected_candidate_id,
                finalCode: event.complete!.final_code,
                endTime: Date.now(),
            }));

            onComplete?.(event.complete.final_code, event.complete.overall_confidence);
        }

        // Error
        if (event.error) {
            setState(prev => ({
                ...prev,
                status: 'error',
                error: event.error!.message,
                endTime: Date.now(),
            }));

            onError?.(event.error.message);
        }
    }, [onToken, onCandidate, onVerification, onComplete, onError]);

    /**
     * Cancel ongoing generation
     */
    const cancel = useCallback(async () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        if (state.ivcuId) {
            try {
                await service.cancel(state.ivcuId, 'User cancelled');
            } catch (e) {
                // Ignore cancel errors
            }
        }

        setState(prev => ({
            ...prev,
            status: 'cancelled',
            endTime: Date.now(),
        }));
    }, [state.ivcuId, service]);

    /**
     * Select a candidate as the final result
     */
    const selectCandidate = useCallback((candidateId: string) => {
        const candidate = state.candidates.get(candidateId);
        if (candidate) {
            setState(prev => ({
                ...prev,
                selectedCandidateId: candidateId,
                finalCode: candidate.code,
                status: 'complete',
            }));
        }
    }, [state.candidates]);

    /**
     * Reset state
     */
    const reset = useCallback(() => {
        cancel();
        setState({
            status: 'idle',
            ivcuId: null,
            modelId: null,
            modelName: null,
            currentTokens: '',
            tokenCount: 0,
            candidates: new Map(),
            selectedCandidateId: null,
            finalCode: null,
            verificationProgress: [],
            cost: null,
            startTime: null,
            endTime: null,
            error: null,
        });
    }, [cancel]);

    /**
     * Get generation status
     */
    const getStatus = useCallback(async () => {
        if (!state.ivcuId) return null;
        return service.getStatus(state.ivcuId);
    }, [state.ivcuId, service]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    // Computed values
    const elapsedMs = state.startTime
        ? (state.endTime || Date.now()) - state.startTime
        : 0;

    const isGenerating = state.status === 'generating';
    const isVerifying = state.status === 'verifying';
    const isComplete = state.status === 'complete';
    const hasError = state.status === 'error';

    const passingCandidates = Array.from(state.candidates.values())
        .filter(c => c.verificationPassed);

    return {
        // State
        ...state,

        // Computed
        elapsedMs,
        isGenerating,
        isVerifying,
        isComplete,
        hasError,
        passingCandidates,

        // Actions
        generate,
        cancel,
        selectCandidate,
        reset,
        getStatus,
    };
}

export default useGenerationWithGrpc;
