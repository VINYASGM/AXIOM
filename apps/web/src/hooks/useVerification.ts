/**
 * useVerification - React hook for streaming verification progress
 * 
 * Provides real-time verification tier progress, error display, and confidence tracking.
 */
import { useState, useCallback, useRef, useEffect } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export interface TierResult {
    tier: 'tier_0' | 'tier_1' | 'tier_2' | 'tier_3';
    verifier: string;
    passed: boolean;
    confidence: number;
    executionTimeMs: number;
    errors: VerificationError[];
    warnings: VerificationWarning[];
}

export interface VerificationError {
    line: number;
    column: number;
    endLine: number;
    endColumn: number;
    message: string;
    severity: 'error' | 'warning' | 'info';
}

export interface VerificationWarning {
    line: number;
    message: string;
    code?: string;
}

export interface SyntaxInfo {
    rootType: string;
    nodeCount: number;
    functions: Array<{ name: string; startLine: number; endLine: number }>;
    classes: Array<{ name: string; startLine: number; endLine: number }>;
    imports: string[];
}

export interface VerificationState {
    status: 'idle' | 'verifying' | 'complete' | 'error';
    candidateId: string | null;

    // Tier status
    currentTier: string | null;
    tierResults: Map<string, TierResult>;

    // Overall result
    passed: boolean;
    confidence: number;
    totalTimeMs: number;

    // Errors and warnings
    allErrors: VerificationError[];
    allWarnings: VerificationWarning[];

    // Syntax info (from Tier 0)
    syntaxInfo: SyntaxInfo | null;

    // Error state
    error: string | null;
}

export interface UseVerificationOptions {
    apiUrl?: string;
    onTierComplete?: (tier: TierResult) => void;
    onComplete?: (passed: boolean, confidence: number) => void;
    onError?: (error: string) => void;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useVerification(options: UseVerificationOptions = {}) {
    const {
        apiUrl = '/api/v1/verify',
        onTierComplete,
        onComplete,
        onError,
    } = options;

    const [state, setState] = useState<VerificationState>({
        status: 'idle',
        candidateId: null,
        currentTier: null,
        tierResults: new Map(),
        passed: false,
        confidence: 0,
        totalTimeMs: 0,
        allErrors: [],
        allWarnings: [],
        syntaxInfo: null,
        error: null,
    });

    const abortControllerRef = useRef<AbortController | null>(null);

    // Quick verify (Tier 0 only, synchronous)
    const quickVerify = useCallback(async (code: string, language = 'python') => {
        try {
            const response = await fetch(`${apiUrl}/quick`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, language }),
            });

            if (!response.ok) {
                throw new Error(`Verification failed: ${response.statusText}`);
            }

            const result = await response.json();

            const errors: VerificationError[] = (result.errors || []).map((e: any) => ({
                line: e.line,
                column: e.column,
                endLine: e.end_line,
                endColumn: e.end_column,
                message: e.message,
                severity: e.severity || 'error',
            }));

            const syntaxInfo: SyntaxInfo = {
                rootType: result.ast_info?.root_type || '',
                nodeCount: result.ast_info?.node_count || 0,
                functions: result.ast_info?.functions || [],
                classes: result.ast_info?.classes || [],
                imports: result.ast_info?.imports || [],
            };

            return {
                passed: result.passed,
                confidence: result.confidence,
                parseTimeMs: result.parse_time_ms,
                errors,
                syntaxInfo,
            };

        } catch (error: any) {
            console.error('Quick verify error:', error);
            return {
                passed: false,
                confidence: 0,
                parseTimeMs: 0,
                errors: [{
                    line: 1, column: 0, endLine: 1, endColumn: 0,
                    message: error.message,
                    severity: 'error' as const
                }],
                syntaxInfo: null,
            };
        }
    }, [apiUrl]);

    // Full verification with streaming
    const verify = useCallback(async (
        code: string,
        language = 'python',
        options: {
            runTier0?: boolean;
            runTier1?: boolean;
            runTier2?: boolean;
            runTier3?: boolean;
            candidateId?: string;
        } = {}
    ) => {
        // Cancel any existing verification
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();

        setState(prev => ({
            ...prev,
            status: 'verifying',
            candidateId: options.candidateId || null,
            currentTier: null,
            tierResults: new Map(),
            passed: false,
            confidence: 0,
            totalTimeMs: 0,
            allErrors: [],
            allWarnings: [],
            syntaxInfo: null,
            error: null,
        }));

        try {
            const response = await fetch(`${apiUrl}/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream',
                },
                body: JSON.stringify({
                    code,
                    language,
                    candidate_id: options.candidateId,
                    options: {
                        run_tier0: options.runTier0 ?? true,
                        run_tier1: options.runTier1 ?? true,
                        run_tier2: options.runTier2 ?? false,
                        run_tier3: options.runTier3 ?? false,
                        fail_fast: true,
                    },
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`Verification failed: ${response.statusText}`);
            }

            if (!response.body) {
                throw new Error('No response body');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;

                        try {
                            const event = JSON.parse(data);
                            handleVerificationEvent(event);
                        } catch (e) {
                            console.error('Failed to parse event:', e);
                        }
                    }
                }
            }

        } catch (error: any) {
            if (error.name === 'AbortError') {
                setState(prev => ({ ...prev, status: 'idle' }));
            } else {
                const errorMsg = error.message || 'Verification failed';
                setState(prev => ({
                    ...prev,
                    status: 'error',
                    error: errorMsg,
                }));
                onError?.(errorMsg);
            }
        }
    }, [apiUrl, onError]);

    // Handle verification events
    const handleVerificationEvent = useCallback((event: any) => {
        if (event.tier_started) {
            setState(prev => ({
                ...prev,
                currentTier: event.tier_started.tier,
            }));
        }

        if (event.tier_complete) {
            const tierResult: TierResult = {
                tier: event.tier_complete.tier,
                verifier: event.tier_complete.results?.[0]?.verifier || 'unknown',
                passed: event.tier_complete.passed,
                confidence: event.tier_complete.confidence,
                executionTimeMs: event.tier_complete.execution_time_ms,
                errors: (event.tier_complete.results || []).flatMap((r: any) =>
                    (r.errors || []).map((e: any) => ({
                        line: e.line || 1,
                        column: e.column || 0,
                        endLine: e.end_line || 1,
                        endColumn: e.end_column || 0,
                        message: typeof e === 'string' ? e : e.message,
                        severity: 'error' as const,
                    }))
                ),
                warnings: (event.tier_complete.results || []).flatMap((r: any) =>
                    (r.warnings || []).map((w: any) => ({
                        line: w.line || 1,
                        message: typeof w === 'string' ? w : w.message,
                    }))
                ),
            };

            setState(prev => {
                const newTierResults = new Map(prev.tierResults);
                newTierResults.set(tierResult.tier, tierResult);
                return {
                    ...prev,
                    tierResults: newTierResults,
                    allErrors: [...prev.allErrors, ...tierResult.errors],
                    allWarnings: [...prev.allWarnings, ...tierResult.warnings],
                    totalTimeMs: prev.totalTimeMs + tierResult.executionTimeMs,
                };
            });

            onTierComplete?.(tierResult);
        }

        if (event.complete) {
            setState(prev => ({
                ...prev,
                status: 'complete',
                passed: event.complete.passed,
                confidence: event.complete.confidence,
                totalTimeMs: event.complete.total_time_ms,
            }));

            onComplete?.(event.complete.passed, event.complete.confidence);
        }

        if (event.error) {
            setState(prev => ({
                ...prev,
                status: 'error',
                error: event.error.message,
            }));

            onError?.(event.error.message);
        }
    }, [onTierComplete, onComplete, onError]);

    // Cancel verification
    const cancel = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setState(prev => ({ ...prev, status: 'idle' }));
    }, []);

    // Reset state
    const reset = useCallback(() => {
        cancel();
        setState({
            status: 'idle',
            candidateId: null,
            currentTier: null,
            tierResults: new Map(),
            passed: false,
            confidence: 0,
            totalTimeMs: 0,
            allErrors: [],
            allWarnings: [],
            syntaxInfo: null,
            error: null,
        });
    }, [cancel]);

    // Cleanup
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    // Computed values
    const isVerifying = state.status === 'verifying';
    const isComplete = state.status === 'complete';
    const hasErrors = state.allErrors.length > 0;
    const hasWarnings = state.allWarnings.length > 0;

    const tier0Result = state.tierResults.get('tier_0');
    const tier1Result = state.tierResults.get('tier_1');
    const tier2Result = state.tierResults.get('tier_2');
    const tier3Result = state.tierResults.get('tier_3');

    return {
        // State
        ...state,

        // Tier results (convenience)
        tier0Result,
        tier1Result,
        tier2Result,
        tier3Result,

        // Computed
        isVerifying,
        isComplete,
        hasErrors,
        hasWarnings,

        // Actions
        quickVerify,
        verify,
        cancel,
        reset,
    };
}
