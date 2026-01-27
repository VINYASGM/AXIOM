'use client';

/**
 * VerificationProgress - Component for displaying verification tier progress
 * 
 * Shows real-time verification progress with tier-by-tier breakdown,
 * error/warning display, and confidence meters.
 */
import React from 'react';
import { TierResult, VerificationError, VerificationWarning } from '../hooks/useVerification';

// ============================================================================
// TYPES
// ============================================================================

type TierName = 'tier_0' | 'tier_1' | 'tier_2' | 'tier_3';

interface VerificationProgressProps {
    currentTier: TierName | null;
    tierResults: Map<string, TierResult>;
    isVerifying: boolean;
    overallPassed: boolean;
    overallConfidence: number;
    totalTimeMs: number;
    className?: string;
}

// ============================================================================
// TIER CONFIG
// ============================================================================

const tierConfig: Record<TierName, {
    name: string;
    description: string;
    icon: React.ReactNode;
    targetTime: string;
}> = {
    tier_0: {
        name: 'Syntax',
        description: 'Tree-sitter parsing',
        icon: '🌳',
        targetTime: '<10ms',
    },
    tier_1: {
        name: 'Static',
        description: 'Type checking & linting',
        icon: '🔍',
        targetTime: '<2s',
    },
    tier_2: {
        name: 'Dynamic',
        description: 'Unit tests & property tests',
        icon: '🧪',
        targetTime: '2-15s',
    },
    tier_3: {
        name: 'Formal',
        description: 'SMT solving & fuzzing',
        icon: '🔒',
        targetTime: '15s-5min',
    },
};

const tierOrder: TierName[] = ['tier_0', 'tier_1', 'tier_2', 'tier_3'];

// ============================================================================
// TIER ITEM
// ============================================================================

interface TierItemProps {
    tier: TierName;
    result?: TierResult;
    isActive: boolean;
    isPending: boolean;
}

function TierItem({ tier, result, isActive, isPending }: TierItemProps) {
    const config = tierConfig[tier];

    // Status determination
    const status = result
        ? (result.passed ? 'passed' : 'failed')
        : (isActive ? 'running' : (isPending ? 'pending' : 'skipped'));

    return (
        <div className={`
      p-4 rounded-xl border-2 transition-all
      ${status === 'passed' ? 'border-emerald-500/50 bg-emerald-500/10' :
                status === 'failed' ? 'border-red-500/50 bg-red-500/10' :
                    status === 'running' ? 'border-blue-500/50 bg-blue-500/10' :
                        'border-zinc-700 bg-zinc-800/50'
            }
    `}>
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <span className="text-lg">{config.icon}</span>
                    <span className="font-semibold text-white">{config.name}</span>
                    <span className="text-xs text-zinc-500">{config.targetTime}</span>
                </div>

                {/* Status indicator */}
                {status === 'running' && (
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                        <span className="text-xs text-blue-400">Running...</span>
                    </div>
                )}
                {status === 'passed' && (
                    <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                )}
                {status === 'failed' && (
                    <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                )}
                {status === 'pending' && (
                    <div className="w-5 h-5 rounded-full border-2 border-zinc-600" />
                )}
            </div>

            {/* Description */}
            <p className="text-sm text-zinc-400 mb-2">{config.description}</p>

            {/* Result details */}
            {result && (
                <div className="space-y-2">
                    {/* Confidence bar */}
                    <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
                            <div
                                className={`h-full transition-all ${result.passed ? 'bg-emerald-500' : 'bg-red-500'
                                    }`}
                                style={{ width: `${result.confidence * 100}%` }}
                            />
                        </div>
                        <span className="text-xs text-zinc-400 font-mono">
                            {Math.round(result.confidence * 100)}%
                        </span>
                    </div>

                    {/* Time */}
                    <div className="text-xs text-zinc-500">
                        Completed in {result.executionTimeMs.toFixed(1)}ms
                    </div>

                    {/* Errors */}
                    {result.errors.length > 0 && (
                        <div className="mt-2 space-y-1">
                            {result.errors.slice(0, 3).map((error, i) => (
                                <div key={i} className="flex items-start gap-2 text-xs text-red-400">
                                    <span className="mt-0.5">✕</span>
                                    <span>
                                        {error.line && `L${error.line}: `}
                                        {error.message}
                                    </span>
                                </div>
                            ))}
                            {result.errors.length > 3 && (
                                <div className="text-xs text-zinc-500">
                                    +{result.errors.length - 3} more errors
                                </div>
                            )}
                        </div>
                    )}

                    {/* Warnings */}
                    {result.warnings.length > 0 && (
                        <div className="mt-2 space-y-1">
                            {result.warnings.slice(0, 2).map((warning, i) => (
                                <div key={i} className="flex items-start gap-2 text-xs text-amber-400">
                                    <span className="mt-0.5">⚠</span>
                                    <span>
                                        {warning.line && `L${warning.line}: `}
                                        {warning.message}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Running animation */}
            {status === 'running' && (
                <div className="mt-2">
                    <div className="h-1 bg-zinc-700 rounded-full overflow-hidden">
                        <div className="h-full w-1/3 bg-blue-500 rounded-full animate-pulse"
                            style={{ animation: 'pulse 1s ease-in-out infinite, slideRight 1.5s ease-in-out infinite' }} />
                    </div>
                </div>
            )}
        </div>
    );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function VerificationProgress({
    currentTier,
    tierResults,
    isVerifying,
    overallPassed,
    overallConfidence,
    totalTimeMs,
    className = '',
}: VerificationProgressProps) {
    // Determine tier states
    const getTierState = (tier: TierName) => {
        const result = tierResults.get(tier);
        const tierIndex = tierOrder.indexOf(tier);
        const currentIndex = currentTier ? tierOrder.indexOf(currentTier) : -1;

        return {
            result,
            isActive: tier === currentTier && isVerifying,
            isPending: tierIndex > currentIndex && isVerifying,
        };
    };

    return (
        <div className={`space-y-4 ${className}`}>
            {/* Overall status header */}
            <div className={`
        p-4 rounded-xl border-2 
        ${isVerifying ? 'border-blue-500 bg-blue-500/10' :
                    overallPassed ? 'border-emerald-500 bg-emerald-500/10' :
                        'border-red-500 bg-red-500/10'
                }
      `}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {isVerifying ? (
                            <>
                                <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                                <span className="font-semibold text-white">Verifying...</span>
                            </>
                        ) : overallPassed ? (
                            <>
                                <svg className="w-6 h-6 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <span className="font-semibold text-emerald-400">Verification Passed</span>
                            </>
                        ) : (
                            <>
                                <svg className="w-6 h-6 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <span className="font-semibold text-red-400">Verification Failed</span>
                            </>
                        )}
                    </div>

                    <div className="text-right">
                        <div className="text-2xl font-mono text-white">
                            {Math.round(overallConfidence * 100)}%
                        </div>
                        <div className="text-xs text-zinc-500">
                            {totalTimeMs > 0 ? `${totalTimeMs.toFixed(0)}ms` : '—'}
                        </div>
                    </div>
                </div>
            </div>

            {/* Tier breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {tierOrder.map(tier => {
                    const { result, isActive, isPending } = getTierState(tier);
                    return (
                        <TierItem
                            key={tier}
                            tier={tier}
                            result={result}
                            isActive={isActive}
                            isPending={isPending}
                        />
                    );
                })}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-emerald-500" />
                    <span>Passed</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span>Failed</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
                    <span>Running</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full border-2 border-zinc-600" />
                    <span>Pending</span>
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// COMPACT VERSION
// ============================================================================

interface CompactVerificationProps {
    tierResults: Map<string, TierResult>;
    isVerifying: boolean;
    className?: string;
}

export function CompactVerification({
    tierResults,
    isVerifying,
    className = '',
}: CompactVerificationProps) {
    return (
        <div className={`flex items-center gap-2 ${className}`}>
            {tierOrder.map(tier => {
                const result = tierResults.get(tier);
                const config = tierConfig[tier];

                return (
                    <div
                        key={tier}
                        className={`
              flex items-center gap-1 px-2 py-1 rounded text-xs
              ${result?.passed ? 'bg-emerald-500/20 text-emerald-400' :
                                result && !result.passed ? 'bg-red-500/20 text-red-400' :
                                    isVerifying ? 'bg-zinc-700 text-zinc-400' :
                                        'bg-zinc-800 text-zinc-600'
                            }
            `}
                        title={`${config.name}: ${config.description}`}
                    >
                        <span>{config.icon}</span>
                        {result && (
                            <span className="font-mono">{Math.round(result.confidence * 100)}%</span>
                        )}
                        {!result && isVerifying && tier === tierOrder.find(t => !tierResults.has(t)) && (
                            <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default VerificationProgress;
