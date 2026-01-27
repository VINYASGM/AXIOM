/**
 * useModelSelector - React hook for model selection and tier management
 * 
 * Provides model catalog, tier filtering, cost estimation, and recommendations.
 */
import { useState, useCallback, useEffect, useMemo } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export type ModelTier = 'local' | 'balanced' | 'high_accuracy' | 'frontier';
export type TaskComplexity = 'simple' | 'medium' | 'complex' | 'critical';

export interface ModelSpec {
    id: string;
    name: string;
    provider: string;
    tier: ModelTier;
    humanEvalScore: number;
    contextWindow: number;
    inputCostPer1M: number;
    outputCostPer1M: number;
    available: boolean;
    isLocal: boolean;
    capabilities: string[];
}

export interface CostEstimate {
    modelId: string;
    baseCost: number;
    effectiveCost: number;
    retryMultiplier: number;
    estimatedTokens: {
        input: number;
        output: number;
    };
}

export interface ModelSelectorState {
    models: ModelSpec[];
    selectedModelId: string | null;
    selectedTier: ModelTier | null;
    isLoading: boolean;
    error: string | null;
}

export interface UseModelSelectorOptions {
    apiUrl?: string;
    defaultTier?: ModelTier;
    autoSelect?: boolean;
    onSelect?: (model: ModelSpec) => void;
}

// ============================================================================
// MODEL CATALOG (CLIENT-SIDE MIRROR)
// ============================================================================

const MODEL_CATALOG: ModelSpec[] = [
    // LOCAL TIER
    {
        id: 'qwen3-8b',
        name: 'Qwen 3 8B',
        provider: 'local',
        tier: 'local',
        humanEvalScore: 72.0,
        contextWindow: 32768,
        inputCostPer1M: 0,
        outputCostPer1M: 0,
        available: true,
        isLocal: true,
        capabilities: ['code_generation', 'reasoning'],
    },
    {
        id: 'gemma3-4b',
        name: 'Gemma 3 4B',
        provider: 'local',
        tier: 'local',
        humanEvalScore: 65.0,
        contextWindow: 8192,
        inputCostPer1M: 0,
        outputCostPer1M: 0,
        available: true,
        isLocal: true,
        capabilities: ['code_generation'],
    },
    {
        id: 'deepseek-coder-v2-7b',
        name: 'DeepSeek Coder V2 7B',
        provider: 'local',
        tier: 'local',
        humanEvalScore: 78.0,
        contextWindow: 32768,
        inputCostPer1M: 0,
        outputCostPer1M: 0,
        available: true,
        isLocal: true,
        capabilities: ['code_generation', 'debugging'],
    },

    // BALANCED TIER
    {
        id: 'deepseek-v3',
        name: 'DeepSeek V3',
        provider: 'deepseek',
        tier: 'balanced',
        humanEvalScore: 88.5,
        contextWindow: 128000,
        inputCostPer1M: 0.14,
        outputCostPer1M: 0.28,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning', 'debugging'],
    },
    {
        id: 'claude-3-5-haiku',
        name: 'Claude 3.5 Haiku',
        provider: 'anthropic',
        tier: 'balanced',
        humanEvalScore: 82.0,
        contextWindow: 200000,
        inputCostPer1M: 0.80,
        outputCostPer1M: 4.00,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning'],
    },
    {
        id: 'gemini-2-flash',
        name: 'Gemini 2.0 Flash',
        provider: 'google',
        tier: 'balanced',
        humanEvalScore: 83.5,
        contextWindow: 1000000,
        inputCostPer1M: 0.075,
        outputCostPer1M: 0.30,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'multimodal'],
    },
    {
        id: 'gpt-4o-mini',
        name: 'GPT-4o Mini',
        provider: 'openai',
        tier: 'balanced',
        humanEvalScore: 87.2,
        contextWindow: 128000,
        inputCostPer1M: 0.15,
        outputCostPer1M: 0.60,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning'],
    },

    // HIGH ACCURACY TIER
    {
        id: 'claude-sonnet-4',
        name: 'Claude Sonnet 4',
        provider: 'anthropic',
        tier: 'high_accuracy',
        humanEvalScore: 93.7,
        contextWindow: 200000,
        inputCostPer1M: 3.00,
        outputCostPer1M: 15.00,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning', 'debugging', 'documentation'],
    },
    {
        id: 'gpt-4o',
        name: 'GPT-4o',
        provider: 'openai',
        tier: 'high_accuracy',
        humanEvalScore: 90.2,
        contextWindow: 128000,
        inputCostPer1M: 2.50,
        outputCostPer1M: 10.00,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning', 'debugging'],
    },
    {
        id: 'gemini-2-pro',
        name: 'Gemini 2.0 Pro',
        provider: 'google',
        tier: 'high_accuracy',
        humanEvalScore: 89.0,
        contextWindow: 2000000,
        inputCostPer1M: 1.25,
        outputCostPer1M: 5.00,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning', 'multimodal'],
    },

    // FRONTIER TIER
    {
        id: 'claude-opus-4',
        name: 'Claude Opus 4',
        provider: 'anthropic',
        tier: 'frontier',
        humanEvalScore: 96.5,
        contextWindow: 200000,
        inputCostPer1M: 15.00,
        outputCostPer1M: 75.00,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning', 'debugging', 'formal_verification'],
    },
    {
        id: 'openai-o1',
        name: 'OpenAI o1',
        provider: 'openai',
        tier: 'frontier',
        humanEvalScore: 94.5,
        contextWindow: 200000,
        inputCostPer1M: 15.00,
        outputCostPer1M: 60.00,
        available: true,
        isLocal: false,
        capabilities: ['code_generation', 'reasoning', 'debugging', 'novel_problems'],
    },
];

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useModelSelector(options: UseModelSelectorOptions = {}) {
    const {
        apiUrl = '/api/v1/models',
        defaultTier = 'balanced',
        autoSelect = true,
        onSelect,
    } = options;

    const [state, setState] = useState<ModelSelectorState>({
        models: MODEL_CATALOG,
        selectedModelId: null,
        selectedTier: defaultTier,
        isLoading: false,
        error: null,
    });

    // Filter models by tier
    const modelsByTier = useMemo(() => {
        const byTier: Record<ModelTier, ModelSpec[]> = {
            local: [],
            balanced: [],
            high_accuracy: [],
            frontier: [],
        };

        for (const model of state.models) {
            byTier[model.tier].push(model);
        }

        return byTier;
    }, [state.models]);

    // Get models for selected tier
    const currentTierModels = useMemo(() => {
        if (!state.selectedTier) return state.models;
        return modelsByTier[state.selectedTier];
    }, [state.selectedTier, modelsByTier, state.models]);

    // Selected model
    const selectedModel = useMemo(() => {
        if (!state.selectedModelId) return null;
        return state.models.find(m => m.id === state.selectedModelId) || null;
    }, [state.selectedModelId, state.models]);

    // Auto-select best model in tier
    useEffect(() => {
        if (autoSelect && state.selectedTier && !state.selectedModelId) {
            const tierModels = modelsByTier[state.selectedTier];
            if (tierModels.length > 0) {
                // Select highest accuracy model in tier
                const best = tierModels.reduce((a, b) =>
                    b.humanEvalScore > a.humanEvalScore ? b : a
                );
                setState(prev => ({ ...prev, selectedModelId: best.id }));
            }
        }
    }, [autoSelect, state.selectedTier, state.selectedModelId, modelsByTier]);

    // Select model
    const selectModel = useCallback((modelId: string) => {
        const model = state.models.find(m => m.id === modelId);
        if (model) {
            setState(prev => ({
                ...prev,
                selectedModelId: modelId,
                selectedTier: model.tier,
            }));
            onSelect?.(model);
        }
    }, [state.models, onSelect]);

    // Select tier
    const selectTier = useCallback((tier: ModelTier) => {
        setState(prev => ({
            ...prev,
            selectedTier: tier,
            selectedModelId: null, // Clear selection when tier changes
        }));
    }, []);

    // Estimate cost for model
    const estimateCost = useCallback((
        modelId: string,
        inputTokens: number,
        outputTokens: number
    ): CostEstimate | null => {
        const model = state.models.find(m => m.id === modelId);
        if (!model) return null;

        const baseCost = (
            (inputTokens / 1_000_000) * model.inputCostPer1M +
            (outputTokens / 1_000_000) * model.outputCostPer1M
        );

        // Calculate retry multiplier based on accuracy
        const passRate = model.humanEvalScore / 100;
        const retryMultiplier = passRate > 0 ? 1 / passRate : 2;

        return {
            modelId,
            baseCost,
            effectiveCost: baseCost * retryMultiplier,
            retryMultiplier,
            estimatedTokens: { input: inputTokens, output: outputTokens },
        };
    }, [state.models]);

    // Recommend model for complexity
    const recommendModel = useCallback((complexity: TaskComplexity): ModelSpec | null => {
        const tierForComplexity: Record<TaskComplexity, ModelTier> = {
            simple: 'local',
            medium: 'balanced',
            complex: 'high_accuracy',
            critical: 'frontier',
        };

        const tier = tierForComplexity[complexity];
        const tierModels = modelsByTier[tier].filter(m => m.available);

        if (tierModels.length === 0) return null;

        // Return highest accuracy available
        return tierModels.reduce((a, b) =>
            b.humanEvalScore > a.humanEvalScore ? b : a
        );
    }, [modelsByTier]);

    // Get next tier model (for upgrade on failure)
    const getNextTierModel = useCallback((currentModelId: string): ModelSpec | null => {
        const current = state.models.find(m => m.id === currentModelId);
        if (!current) return null;

        const tierOrder: ModelTier[] = ['local', 'balanced', 'high_accuracy', 'frontier'];
        const currentIdx = tierOrder.indexOf(current.tier);

        if (currentIdx >= tierOrder.length - 1) return null;

        // Get models from next tier
        const nextTier = tierOrder[currentIdx + 1];
        const nextTierModels = modelsByTier[nextTier].filter(m => m.available);

        if (nextTierModels.length === 0) return null;

        return nextTierModels.reduce((a, b) =>
            b.humanEvalScore > a.humanEvalScore ? b : a
        );
    }, [state.models, modelsByTier]);

    // Refresh models from API
    const refreshModels = useCallback(async () => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error('Failed to fetch models');
            }

            const data = await response.json();

            // Update availability from API
            const updatedModels = state.models.map(model => {
                const apiModel = data.models?.find((m: any) => m.id === model.id);
                return apiModel ? { ...model, available: apiModel.available } : model;
            });

            setState(prev => ({
                ...prev,
                models: updatedModels,
                isLoading: false,
            }));

        } catch (error: any) {
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: error.message,
            }));
        }
    }, [apiUrl, state.models]);

    // Computed values
    const availableModels = useMemo(() =>
        state.models.filter(m => m.available),
        [state.models]
    );

    const localModels = useMemo(() =>
        state.models.filter(m => m.isLocal),
        [state.models]
    );

    const cloudModels = useMemo(() =>
        state.models.filter(m => !m.isLocal),
        [state.models]
    );

    return {
        // State
        ...state,
        selectedModel,
        currentTierModels,
        modelsByTier,

        // Computed
        availableModels,
        localModels,
        cloudModels,

        // Actions
        selectModel,
        selectTier,
        estimateCost,
        recommendModel,
        getNextTierModel,
        refreshModels,
    };
}
