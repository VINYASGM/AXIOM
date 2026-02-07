'use client';

/**
 * ModelSelector - UI component for selecting AI models
 * 
 * Displays model tiers, cost estimates, and allows model selection.
 * Integrates with useModelSelector hook.
 */
import React, { useState } from 'react';
import { useModelSelector, ModelTier, ModelSpec, TaskComplexity } from '../hooks/useModelSelector';

// ============================================================================
// TIER BADGE
// ============================================================================

interface TierBadgeProps {
    tier: ModelTier;
    selected?: boolean;
    onClick?: () => void;
}

const tierConfig: Record<ModelTier, { label: string; color: string; description: string }> = {
    local: {
        label: 'Local',
        color: 'bg-emerald-500',
        description: 'Privacy-first, no cost'
    },
    balanced: {
        label: 'Balanced',
        color: 'bg-blue-500',
        description: 'Best value for most tasks'
    },
    high_accuracy: {
        label: 'High Accuracy',
        color: 'bg-purple-500',
        description: 'Complex debugging & architecture'
    },
    frontier: {
        label: 'Frontier',
        color: 'bg-amber-500',
        description: 'Novel problems requiring top reasoning'
    },
};

function TierBadge({ tier, selected, onClick }: TierBadgeProps) {
    const config = tierConfig[tier];

    return (
        <button
            onClick={onClick}
            className={`
        px-4 py-2 rounded-lg font-medium transition-all
        ${selected
                    ? `${config.color} text-white shadow-lg scale-105`
                    : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                }
      `}
        >
            <span className="block text-sm">{config.label}</span>
            <span className="block text-xs opacity-75">{config.description}</span>
        </button>
    );
}

// ============================================================================
// MODEL CARD
// ============================================================================

interface ModelCardProps {
    model: ModelSpec;
    selected?: boolean;
    onSelect?: () => void;
    estimatedCost?: number;
}

function ModelCard({ model, selected, onSelect, estimatedCost }: ModelCardProps) {
    return (
        <div
            onClick={onSelect}
            className={`
        p-4 rounded-xl border-2 cursor-pointer transition-all
        ${selected
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-zinc-700 bg-zinc-800/50 hover:border-zinc-600'
                }
        ${!model.available && 'opacity-50 cursor-not-allowed'}
      `}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-white">{model.name}</h3>
                {model.isLocal && (
                    <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">
                        LOCAL
                    </span>
                )}
            </div>

            {/* Provider */}
            <p className="text-sm text-zinc-400 mb-3">{model.provider}</p>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2 text-sm">
                {/* Accuracy */}
                <div className="flex items-center gap-2">
                    <div
                        className="h-2 flex-1 bg-zinc-700 rounded-full overflow-hidden"
                    >
                        <div
                            className="h-full bg-gradient-to-r from-emerald-500 to-blue-500"
                            style={{ width: `${model.humanEvalScore}%` }}
                        />
                    </div>
                    <span className="text-zinc-300 font-mono text-xs">
                        {model.humanEvalScore}%
                    </span>
                </div>

                {/* Context */}
                <div className="text-zinc-400 text-xs">
                    {formatTokens(model.contextWindow)} ctx
                </div>

                {/* Cost */}
                <div className="col-span-2 text-zinc-400 text-xs">
                    {model.isLocal ? (
                        <span className="text-emerald-400">Free (local)</span>
                    ) : (
                        <>
                            ${model.inputCostPer1M}/M in • ${model.outputCostPer1M}/M out
                        </>
                    )}
                </div>

                {/* Estimated cost for this task */}
                {estimatedCost !== undefined && estimatedCost > 0 && (
                    <div className="col-span-2 pt-2 border-t border-zinc-700">
                        <span className="text-zinc-500">Est. cost: </span>
                        <span className="text-white font-mono">${estimatedCost.toFixed(4)}</span>
                    </div>
                )}
            </div>

            {/* Capabilities */}
            <div className="flex flex-wrap gap-1 mt-3">
                {model.capabilities.slice(0, 3).map(cap => (
                    <span
                        key={cap}
                        className="px-2 py-0.5 text-xs bg-zinc-700/50 text-zinc-400 rounded"
                    >
                        {cap.replace('_', ' ')}
                    </span>
                ))}
            </div>

            {/* Selection indicator */}
            {selected && (
                <div className="mt-3 flex items-center gap-2 text-blue-400 text-sm">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Selected
                </div>
            )}
        </div>
    );
}

// ============================================================================
// COST COMPARISON
// ============================================================================

interface CostComparisonProps {
    models: ModelSpec[];
    selectedModelId: string | null;
    onSelect: (modelId: string) => void;
}

function CostComparison({ models, selectedModelId, onSelect }: CostComparisonProps) {
    // Estimate tokens for comparison (1000 input, 500 output)
    const estimates = models.map(model => {
        const baseCost = (1000 / 1_000_000) * model.inputCostPer1M +
            (500 / 1_000_000) * model.outputCostPer1M;
        const passRate = model.humanEvalScore / 100;
        const effectiveCost = passRate > 0 ? baseCost / passRate : baseCost * 2;

        return {
            model,
            baseCost,
            effectiveCost,
        };
    }).sort((a, b) => a.effectiveCost - b.effectiveCost);

    return (
        <div className="bg-zinc-800/50 rounded-xl p-4">
            <h4 className="text-sm font-medium text-zinc-300 mb-3">
                Cost Comparison (1K tokens)
            </h4>
            <div className="space-y-2">
                {estimates.map(({ model, baseCost, effectiveCost }) => (
                    <div
                        key={model.id}
                        onClick={() => onSelect(model.id)}
                        className={`
              flex items-center gap-3 p-2 rounded-lg cursor-pointer
              ${model.id === selectedModelId
                                ? 'bg-blue-500/20 border border-blue-500/50'
                                : 'hover:bg-zinc-700/50'
                            }
            `}
                    >
                        <span className="flex-1 text-sm text-zinc-300">{model.name}</span>
                        <span className="text-xs text-zinc-500">
                            ${baseCost.toFixed(4)} base
                        </span>
                        <span className={`text-sm font-mono ${effectiveCost === estimates[0].effectiveCost
                                ? 'text-emerald-400'
                                : 'text-zinc-300'
                            }`}>
                            ${effectiveCost.toFixed(4)}
                        </span>
                        {effectiveCost === estimates[0].effectiveCost && (
                            <span className="text-xs text-emerald-400">BEST</span>
                        )}
                    </div>
                ))}
            </div>
            <p className="text-xs text-zinc-500 mt-3">
                Effective cost = base cost ÷ pass rate (accounts for retries)
            </p>
        </div>
    );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface ModelSelectorProps {
    onModelSelect?: (model: ModelSpec) => void;
    showCostComparison?: boolean;
    complexity?: TaskComplexity;
    className?: string;
}

export function ModelSelector({
    onModelSelect,
    showCostComparison = true,
    complexity,
    className = '',
}: ModelSelectorProps) {
    const {
        selectedModel,
        selectedTier,
        currentTierModels,
        selectModel,
        selectTier,
        recommendModel,
        estimateCost,
    } = useModelSelector({
        autoSelect: true,
        onSelect: onModelSelect,
    });

    // Get recommendation if complexity provided
    const recommended = complexity ? recommendModel(complexity) : null;

    // Calculate estimated costs
    const getEstimatedCost = (modelId: string) => {
        const estimate = estimateCost(modelId, 1000, 500);
        return estimate?.effectiveCost || 0;
    };

    return (
        <div className={`space-y-6 ${className}`}>
            {/* Recommendation */}
            {recommended && (
                <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                        <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
                        </svg>
                        <span className="text-blue-400 font-medium">Recommended for {complexity}</span>
                    </div>
                    <button
                        onClick={() => selectModel(recommended.id)}
                        className={`
              w-full text-left p-3 rounded-lg border transition-all
              ${selectedModel?.id === recommended.id
                                ? 'border-blue-500 bg-blue-500/20'
                                : 'border-zinc-700 bg-zinc-800/50 hover:border-blue-500/50'
                            }
            `}
                    >
                        <span className="font-semibold text-white">{recommended.name}</span>
                        <span className="text-sm text-zinc-400 ml-2">({recommended.humanEvalScore}% accuracy)</span>
                    </button>
                </div>
            )}

            {/* Tier Selection */}
            <div>
                <h3 className="text-sm font-medium text-zinc-400 mb-3">Select Tier</h3>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                    {(['local', 'balanced', 'high_accuracy', 'frontier'] as ModelTier[]).map(tier => (
                        <TierBadge
                            key={tier}
                            tier={tier}
                            selected={selectedTier === tier}
                            onClick={() => selectTier(tier)}
                        />
                    ))}
                </div>
            </div>

            {/* Model Grid */}
            <div>
                <h3 className="text-sm font-medium text-zinc-400 mb-3">
                    {selectedTier ? `${tierConfig[selectedTier].label} Models` : 'All Models'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {currentTierModels.map(model => (
                        <ModelCard
                            key={model.id}
                            model={model}
                            selected={selectedModel?.id === model.id}
                            onSelect={() => model.available && selectModel(model.id)}
                            estimatedCost={getEstimatedCost(model.id)}
                        />
                    ))}
                </div>
            </div>

            {/* Cost Comparison */}
            {showCostComparison && currentTierModels.length > 1 && (
                <CostComparison
                    models={currentTierModels.filter(m => !m.isLocal)}
                    selectedModelId={selectedModel?.id || null}
                    onSelect={selectModel}
                />
            )}

            {/* Selected Model Summary */}
            {selectedModel && (
                <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700">
                    <div className="flex items-center justify-between">
                        <div>
                            <h4 className="font-semibold text-white">{selectedModel.name}</h4>
                            <p className="text-sm text-zinc-400">
                                {selectedModel.humanEvalScore}% accuracy • {selectedModel.provider}
                            </p>
                        </div>
                        <div className="text-right">
                            <div className="text-2xl font-mono text-white">
                                {selectedModel.isLocal ? 'Free' : `$${getEstimatedCost(selectedModel.id).toFixed(4)}`}
                            </div>
                            <div className="text-xs text-zinc-500">per ~1K tokens</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ============================================================================
// HELPERS
// ============================================================================

function formatTokens(tokens: number): string {
    if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
    if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(0)}K`;
    return tokens.toString();
}

export default ModelSelector;
