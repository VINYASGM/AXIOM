
import { GoogleGenAI, Type } from "@google/genai";
import { ModelTier } from "../types";

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const parseIntent = async (prompt: string, complexity: number = 5, tier: ModelTier = ModelTier.Fast) => {
  try {
    const response = await fetch(`${API_BASE}/parse-intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: prompt })
    });

    if (!response.ok) throw new Error("Backend parse failed");

    const data = await response.json();

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

export const generateVerifiedCode = async (intent: string, constraints: string[], complexity: number = 5, tier: ModelTier = ModelTier.Fast) => {
  try {
    // We use the new Parallel Generation endpoint
    const response = await fetch(`${API_BASE}/generate/parallel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sdo_id: "adhoc", // Or pass sdo_id from parse step if we threaded it
        intent: intent,
        language: "python", // Defaulting to Python as per backend focus
        candidate_count: tier === ModelTier.Frontier ? 5 : 3
      })
    });

    if (!response.ok) throw new Error("Backend generation failed");

    const data = await response.json();

    // Check if we have selected code
    if (data.selected_code) return data.selected_code;

    // Fallback if no selected code
    if (data.candidates && data.candidates.length > 0) {
      return data.candidates[0].code;
    }

    return "# Generation failed or no candidates produced.";


  } catch (e) {
    console.error("Generation Error:", e);
    return `# Error generating code: ${e}`;
  }
};

export const snapshotState = async (sdoId: string) => {
  try {
    const response = await fetch(`${API_BASE}/sdo/${sdoId}/snapshot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    return response.ok;
  } catch (e) {
    console.error("Snapshot Error:", e);
    return false;
  }
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
  try {
    const url = tier
      ? `${API_BASE}/api/v1/models?tier=${tier}`
      : `${API_BASE}/api/v1/models`;

    const response = await fetch(url);
    if (!response.ok) throw new Error("Models fetch failed");
    return await response.json();
  } catch (e) {
    console.error("Get Models Error:", e);
    return { models: [], count: 0, cache_age_seconds: null };
  }
};

/**
 * Get the recommended default model.
 * @param tier Optional tier filter
 */
export const getDefaultModel = async (tier?: string): Promise<ModelConfig | null> => {
  try {
    const url = tier
      ? `${API_BASE}/api/v1/models/default?tier=${tier}`
      : `${API_BASE}/api/v1/models/default`;

    const response = await fetch(url);
    if (!response.ok) return null;
    return await response.json();
  } catch (e) {
    console.error("Get Default Model Error:", e);
    return null;
  }
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
  try {
    const response = await fetch(`${API_BASE}/cost/estimate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        intent,
        model
      })
    });

    if (!response.ok) throw new Error("Cost estimate failed");
    return await response.json();
  } catch (e) {
    console.error("Cost Estimate Error:", e);
    return {
      estimated_cost_usd: 0,
      input_tokens: 0,
      output_tokens: 0,
      model: "unknown"
    };
  }
};

export const getGraphData = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/v1/graph`);
    if (!response.ok) throw new Error("Graph fetch failed");
    return await response.json();
  } catch (e) {
    console.error("Graph Data Error:", e);
    return { nodes: [], edges: [] };
  }
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
