'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, AlertTriangle, ChevronDown, ChevronRight, Shield, Zap, TestTube, FileCode } from 'lucide-react';
import { useState } from 'react';

// Define the interface here inline to avoid import issues if not in shared types yet
interface VerifierResult {
    name: string;
    tier: string;
    passed: boolean;
    confidence: number;
    details?: Record<string, any>;
    errors?: string[];
    warnings?: string[];
}

interface VerificationBreakdownProps {
    verificationResult: {
        passed: boolean;
        confidence: number;
        tier_1_passed?: boolean; // Changed to optional to match AxiomStore
        tier_2_passed?: boolean;
        total_errors?: number; // Changed to optional
        total_warnings?: number; // Changed to optional
        verifier_results?: VerifierResult[]; // Changed to optional
        verifierResults?: VerifierResult[]; // Handle both snake_case and camelCase
        totalErrors?: number;
        totalWarnings?: number;
        tier1Passed?: boolean;
        tier2Passed?: boolean;
    } | null;
    compact?: boolean;
}

// Icon mapping for verifiers
const verifierIcons: Record<string, React.ElementType> = {
    syntax: FileCode,
    ast_analysis: Shield,
    type_check: Zap,
    unit_tests: TestTube,
    contract_verify: Shield,
};

export function VerificationBreakdown({ verificationResult, compact = false }: VerificationBreakdownProps) {
    const [expandedTiers, setExpandedTiers] = useState<Set<string>>(new Set(['tier_1']));
    const [expandedVerifiers, setExpandedVerifiers] = useState<Set<string>>(new Set());

    if (!verificationResult) {
        return (
            <div className="text-gray-500 text-sm p-4 text-center">

            </div>
        );
    }

    // Normalize properties (handle snake_case vs camelCase from different API versions)
    const tier1Passed = verificationResult.tier1Passed ?? verificationResult.tier_1_passed ?? false;
    const tier2Passed = verificationResult.tier2Passed ?? verificationResult.tier_2_passed; // could be undefined
    const totalErrors = verificationResult.totalErrors ?? verificationResult.total_errors ?? 0;
    const totalWarnings = verificationResult.totalWarnings ?? verificationResult.total_warnings ?? 0;
    const verifierResults = verificationResult.verifierResults ?? verificationResult.verifier_results ?? [];


    const toggleTier = (tier: string) => {
        const newExpanded = new Set(expandedTiers);
        if (newExpanded.has(tier)) {
            newExpanded.delete(tier);
        } else {
            newExpanded.add(tier);
        }
        setExpandedTiers(newExpanded);
    };

    const toggleVerifier = (name: string) => {
        const newExpanded = new Set(expandedVerifiers);
        if (newExpanded.has(name)) {
            newExpanded.delete(name);
        } else {
            newExpanded.add(name);
        }
        setExpandedVerifiers(newExpanded);
    };

    // Group results by tier
    const tier1Results = verifierResults.filter(r => r.tier === 'TIER_1') || [];
    const tier2Results = verifierResults.filter(r => r.tier === 'TIER_2') || [];

    const renderVerifierResult = (result: VerifierResult) => {
        const isExpanded = expandedVerifiers.has(result.name);
        const Icon = verifierIcons[result.name] || Shield;
        const hasDetails = (result.errors?.length || 0) > 0 || (result.warnings?.length || 0) > 0 || Object.keys(result.details || {}).length > 0;

        return (
            <motion.div
                key={result.name}
                className="ml-4 mb-2"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <div
                    className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${result.passed ? 'hover:bg-green-500/10' : 'hover:bg-red-500/10'
                        }`}
                    onClick={() => hasDetails && toggleVerifier(result.name)}
                >
                    {hasDetails && (
                        isExpanded ?
                            <ChevronDown className="w-3 h-3 text-gray-400" /> :
                            <ChevronRight className="w-3 h-3 text-gray-400" />
                    )}

                    <Icon className={`w-4 h-4 ${result.passed ? 'text-green-400' : 'text-red-400'}`} />

                    <span className="text-sm font-medium capitalize">
                        {result.name.replace(/_/g, ' ')}
                    </span>

                    {result.passed ? (
                        <Check className="w-4 h-4 text-green-400 ml-auto" />
                    ) : (
                        <X className="w-4 h-4 text-red-400 ml-auto" />
                    )}

                    <span className={`text-xs px-2 py-0.5 rounded-full ${result.confidence >= 0.8 ? 'bg-green-500/20 text-green-400' :
                        result.confidence >= 0.5 ? 'bg-amber-500/20 text-amber-400' :
                            'bg-red-500/20 text-red-400'
                        }`}>
                        {Math.round(result.confidence * 100)}%
                    </span>
                </div>

                <AnimatePresence>
                    {isExpanded && hasDetails && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="ml-6 mt-1 overflow-hidden"
                        >
                            {/* Errors */}
                            {result.errors && result.errors.length > 0 && (
                                <div className="mb-2">
                                    <span className="text-xs text-red-400 font-medium">Errors:</span>
                                    {result.errors.map((err, i) => (
                                        <div key={i} className="text-xs text-red-300/80 ml-2 mt-1 font-mono">
                                            {err}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Warnings */}
                            {result.warnings && result.warnings.length > 0 && (
                                <div className="mb-2">
                                    <span className="text-xs text-amber-400 font-medium">Warnings:</span>
                                    {result.warnings.map((warn, i) => (
                                        <div key={i} className="text-xs text-amber-300/80 ml-2 mt-1 font-mono">
                                            {warn}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Details */}
                            {result.details && Object.keys(result.details).length > 0 && (
                                <div className="text-xs text-gray-400">
                                    <details className="cursor-pointer">
                                        <summary className="hover:text-gray-300">Details</summary>
                                        <pre className="mt-1 p-2 bg-black/30 rounded text-xs overflow-auto max-h-40">
                                            {JSON.stringify(result.details, null, 2)}
                                        </pre>
                                    </details>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        );
    };

    const renderTier = (
        title: string,
        tierId: string,
        passed: boolean | undefined,
        results: VerifierResult[]
    ) => {
        const isExpanded = expandedTiers.has(tierId);

        return (
            <div className="mb-3">
                <div
                    className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${passed ? 'bg-green-500/10 border border-green-500/30' :
                        passed === false ? 'bg-red-500/10 border border-red-500/30' :
                            'bg-gray-500/10 border border-gray-500/30'
                        }`}
                    onClick={() => toggleTier(tierId)}
                >
                    {isExpanded ?
                        <ChevronDown className="w-4 h-4 text-gray-400" /> :
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                    }

                    <span className="font-medium">{title}</span>

                    {passed !== undefined && (
                        passed ? (
                            <Check className="w-5 h-5 text-green-400 ml-auto" />
                        ) : (
                            <X className="w-5 h-5 text-red-400 ml-auto" />
                        )
                    )}

                    {passed === undefined && (
                        <span className="text-gray-500 text-sm ml-auto">Skipped</span>
                    )}
                </div>

                <AnimatePresence>
                    {isExpanded && results.length > 0 && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="mt-2 overflow-hidden"
                        >
                            {results.map(renderVerifierResult)}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        );
    };

    if (compact) {
        // Compact summary view
        return (
            <div className="flex items-center gap-4">
                <div className={`flex items-center gap-1 ${tier1Passed ? 'text-green-400' : 'text-red-400'}`}>
                    <Shield className="w-4 h-4" />
                    <span className="text-xs">T1</span>
                    {tier1Passed ?
                        <Check className="w-3 h-3" /> :
                        <X className="w-3 h-3" />
                    }
                </div>

                {tier2Passed !== undefined && (
                    <div className={`flex items-center gap-1 ${tier2Passed ? 'text-green-400' : 'text-red-400'}`}>
                        <TestTube className="w-4 h-4" />
                        <span className="text-xs">T2</span>
                        {tier2Passed ?
                            <Check className="w-3 h-3" /> :
                            <X className="w-3 h-3" />
                        }
                    </div>
                )}

                {totalWarnings > 0 && (
                    <div className="flex items-center gap-1 text-amber-400">
                        <AlertTriangle className="w-3 h-3" />
                        <span className="text-xs">{totalWarnings}</span>
                    </div>
                )}
            </div>
        );
    }

    // Full breakdown view
    return (
        <div className="p-4 rounded-xl bg-black/20 border border-white/5">
            {/* Header */}
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${verificationResult.passed ? 'bg-green-500/20' : 'bg-red-500/20'
                        }`}>
                        {verificationResult.passed ? (
                            <Check className="w-5 h-5 text-green-400" />
                        ) : (
                            <X className="w-5 h-5 text-red-400" />
                        )}
                    </div>
                    <div>
                        <div className="font-medium">
                            {verificationResult.passed ? 'Verification Passed' : 'Verification Failed'}
                        </div>
                        <div className="text-sm text-gray-400">
                            Confidence: {Math.round(verificationResult.confidence * 100)}%
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2 text-sm">
                    {totalErrors > 0 && (
                        <span className="px-2 py-1 rounded bg-red-500/20 text-red-400">
                            {totalErrors} errors
                        </span>
                    )}
                    {totalWarnings > 0 && (
                        <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-400">
                            {totalWarnings} warnings
                        </span>
                    )}
                </div>
            </div>

            {/* Tiers */}
            {renderTier('Tier 1: Static Analysis', 'tier_1', tier1Passed, tier1Results)}
            {renderTier('Tier 2: Dynamic Testing', 'tier_2', tier2Passed, tier2Results)}
        </div>
    );
}
