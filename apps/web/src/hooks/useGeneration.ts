/**
 * useGeneration - React hook for streaming code generation
 * 
 * Provides real-time token streaming, verification progress, and cost tracking.
 * Integrates with AXIOM's bidirectional gRPC streaming API.
 */
import { useState, useCallback, useRef, useEffect } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export interface GenerationToken {
    candidateId: string;
    token: string;
    tokenIndex: number;
    isComplete: boolean;
}

export interface CandidateResult {
    id: string;
    code: string;
    confidence: number;
    reasoning: string;
    tokensUsed: number;
    verificationPassed?: boolean;
    verificationTier?: string;
}

export interface VerificationProgress {
    candidateId: string;
    tier: 'tier_0' | 'tier_1' | 'tier_2' | 'tier_3';
    verifier: string;
    passed: boolean;
    confidence: number;
    errors: string[];
    warnings: string[];
    executionTimeMs: number;
}

export interface CostInfo {
    currentCost: number;
    estimatedRemaining: number;
    modelId: string;
    tokensUsed: number;
}

export interface GenerationState {
    status: 'idle' | 'generating' | 'verifying' | 'complete' | 'error' | 'cancelled';
    ivcuId: string | null;
    modelId: string | null;
    modelName: string | null;

    // Streaming tokens
    currentTokens: string;
    tokenCount: number;

    // Candidates
    candidates: Map<string, CandidateResult>;
    selectedCandidateId: string | null;
    finalCode: string | null;

    // Verification
    verificationProgress: VerificationProgress[];

    // Cost
    cost: CostInfo | null;

    // Timing
    startTime: number | null;
    endTime: number | null;

    // Error
    error: string | null;
}

export interface UseGenerationOptions {
    apiUrl?: string;
    onToken?: (token: GenerationToken) => void;
    onCandidate?: (candidate: CandidateResult) => void;
    onVerification?: (progress: VerificationProgress) => void;
    onComplete?: (code: string, confidence: number) => void;
    onError?: (error: string) => void;
}

export interface GenerationRequest {
    intent: string;
    language?: string;
    modelId?: string;
    contracts?: Array<{
        type: string;
        expression: string;
        description?: string;
    }>;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useGeneration(options: UseGenerationOptions = {}) {
    const {
        apiUrl = '/api/v1/generate',
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

    // Refs for streaming
    const abortControllerRef = useRef<AbortController | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    // Generate code
    const generate = useCallback(async (request: GenerationRequest) => {
        // Cancel any existing generation
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();

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
            // Use Server-Sent Events for streaming (gRPC-Web alternative)
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream',
                },
                body: JSON.stringify({
                    raw_intent: request.intent,
                    language: request.language || 'python',
                    model_id: request.modelId,
                    contracts: request.contracts || [],
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`Generation failed: ${response.statusText}`);
            }

            if (!response.body) {
                throw new Error('No response body');
            }

            // Stream the response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Parse SSE events
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;

                        try {
                            const event = JSON.parse(data);
                            handleStreamEvent(event);
                        } catch (e) {
                            console.error('Failed to parse event:', e);
                        }
                    }
                }
            }

        } catch (error: any) {
            if (error.name === 'AbortError') {
                setState(prev => ({ ...prev, status: 'cancelled' }));
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
    }, [apiUrl, onError]);

    // Handle stream events
    const handleStreamEvent = useCallback((event: any) => {
        const ivcuId = event.ivcu_id;

        if (event.started) {
            setState(prev => ({
                ...prev,
                ivcuId,
                modelId: event.started.model_id,
                modelName: event.started.model_name,
            }));
        }

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

        if (event.verification) {
            const progress: VerificationProgress = {
                candidateId: event.verification.candidate_id,
                tier: event.verification.tier,
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

        if (event.cost) {
            setState(prev => ({
                ...prev,
                cost: {
                    currentCost: event.cost.current_cost,
                    estimatedRemaining: event.cost.estimated_remaining,
                    modelId: event.cost.model_id,
                    tokensUsed: event.cost.tokens_used,
                },
            }));
        }

        if (event.complete) {
            setState(prev => ({
                ...prev,
                status: 'complete',
                selectedCandidateId: event.complete.selected_candidate_id,
                finalCode: event.complete.final_code,
                endTime: Date.now(),
            }));

            onComplete?.(event.complete.final_code, event.complete.overall_confidence);
        }

        if (event.error) {
            setState(prev => ({
                ...prev,
                status: 'error',
                error: event.error.message,
                endTime: Date.now(),
            }));

            onError?.(event.error.message);
        }
    }, [onToken, onCandidate, onVerification, onComplete, onError]);

    // Cancel generation
    const cancel = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }
        setState(prev => ({
            ...prev,
            status: 'cancelled',
            endTime: Date.now(),
        }));
    }, []);

    // Refine intent
    const refine = useCallback(async (refinement: string, clearCandidates = false) => {
        if (!state.ivcuId) return;

        // Send refinement through SSE
        // In full implementation, this would use bidirectional streaming
        await generate({
            intent: refinement,
            language: 'python',
        });
    }, [state.ivcuId, generate]);

    // Select a candidate
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

    // Reset state
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
        refine,
        selectCandidate,
        reset,
    };
}
