
import { GoogleGenAI, Type } from "@google/genai";
import { ModelTier, IVCUStatus } from "../types";

// Always initialize with verified API key from process.env.API_KEY
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || "" });

const getModelForTier = (tier: ModelTier) => {
  switch (tier) {
    case ModelTier.Local: return 'gemini-flash-lite-latest';
    case ModelTier.Fast: return 'gemini-3-flash-preview';
    case ModelTier.Capable: return 'gemini-3-pro-preview';
    case ModelTier.Frontier: return 'gemini-3-pro-preview'; // Research grade mapping
    default: return 'gemini-3-flash-preview';
  }
};

// Backend Integration Service
// Replaces direct Gemini SDK calls with AXIOM Python Backend Requests

import { ApiClient } from "../lib/api";

// Backend Integration Service
// Replaces direct Gemini SDK calls with AXIOM Python Backend Requests

export const parseIntent = async (prompt: string, complexity: number = 5, tier: ModelTier = ModelTier.Fast) => {
  try {
    const data = await ApiClient.parseIntent(prompt, getModelForTier(tier));

    // Map Backend Response to Frontend Expectations
    return {
      interpretation: data.parsed_intent?.summary || "Analyzed intent",
      constraints: data.extracted_constraints || [],
      entities: [], // Backend doesn't explicitly return entities list yet, implies in constraints
      confidence: data.confidence,
      sdo_id: data.sdo_id // Pass through SDO ID for context
    };
  } catch (e) {
    console.error("Parse Intent Error:", e);
    // Fallback or rethrow
    return { interpretation: "Error", constraints: [], entities: [], confidence: 0 };
  }
};

export const generateVerifiedCode = async (intent: string, constraints: string[], complexity: number = 5, tier: ModelTier = ModelTier.Fast, sdoId?: string) => {
  try {
    // 0. Ensure Project Context
    let projectId = localStorage.getItem("axiom_project_id");
    if (!projectId) {
      const projects = await ApiClient.listProjects();
      if (projects.length > 0) {
        projectId = projects[0].id;
      } else {
        const newProject = await ApiClient.createProject("Default Project");
        if (!newProject) throw new Error("Failed to create default project");
        projectId = newProject.id;
      }
      localStorage.setItem("axiom_project_id", projectId);
    }

    // 1. Create IVCU
    // 1. Create IVCU
    const { ivcu_id } = await ApiClient.createIVCU(projectId, intent, sdoId);

    // 2. Start Generation
    // Using default params for now, can be expanded to use 'tier' for strategy if needed
    await ApiClient.startGeneration(
      ivcu_id,
      "python",
      3,
      tier === ModelTier.Frontier ? "frontier" : "simple"
    );

    // 3. Poll for Completion
    const maxAttempts = 60; // 1 minute timeout (approx)
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, 1000)); // Wait 1s

      const status = await ApiClient.getGenerationStatus(ivcu_id);

      if (status.status === IVCUStatus.Verified || status.status === IVCUStatus.Deployed) {
        return status.code;
      }

      if (status.status === IVCUStatus.Failed) {
        throw new Error(`Generation failed: ${status.error || 'Unknown error'}`);
      }
    }

    throw new Error("Generation timed out");

  } catch (e) {
    console.error("Generation Error:", e);
    return `# Error generating code: ${e}`;
  }
};

export const snapshotState = async (sdoId: string) => {
  return await ApiClient.snapshotState(sdoId);
};

// ============================================================================
// Model Configuration API (Dynamic Model Config)
// ============================================================================

export interface ModelConfig {
  name: string;
  provider: string;
  model_id: string;
  tier: string;
  cost_per_1k: number;
  accuracy: number;
  capabilities: Record<string, any>;
  is_active: boolean;
}

export interface ModelsResponse {
  models: ModelConfig[];
  count: number;
  cache_age_seconds: number | null;
}

/**
 * Fetch available model configurations from the backend.
 * @param tier Optional tier filter: 'local', 'balanced', 'high_accuracy', 'frontier'
 */
export const getModels = async (tier?: string): Promise<ModelsResponse> => {
  return await ApiClient.getModels(tier);
};

/**
 * Get the recommended default model.
 * @param tier Optional tier filter
 */
export const getDefaultModel = async (tier?: string): Promise<ModelConfig | null> => {
  return await ApiClient.getDefaultModel(tier);
};

/**
 * Estimate cost for a generation request.
 * @param intent The intent text
 * @param model Model name (e.g., 'deepseek-v3')
 */
export const getEstimatedCost = async (intent: string, model: string = "deepseek-v3"): Promise<{
  estimated_cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  model: string;
}> => {
  return await ApiClient.getEstimatedCost(intent, model);
};

export const getGraphData = async () => {
  return await ApiClient.getGraphData();
};



export const generateIntentVisual = async (intent: string) => {
  const response = await ai.models.generateContent({
    model: 'gemini-2.5-flash-image',
    contents: {
      parts: [{
        text: `Technical architectural blueprint schematic of a software system described as: "${intent}". 
        Visual: Glowing obsidian console, technical blueprint lines, data flow vectors, minimalist scientific instrumentation style. 
        Cinematic lighting, high-tech holographic overlays, 8k resolution.`
      }]
    },
    config: {
      imageConfig: {
        aspectRatio: "16:9"
      }
    }
  });

  const part = response.candidates?.[0]?.content?.parts.find(p => p.inlineData);
  if (part?.inlineData) {
    return `data:${part.inlineData.mimeType};base64,${part.inlineData.data}`;
  }
  return null;
};
