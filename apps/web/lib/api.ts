
import { ModelTier, TeamMember, SpeculationResult, ProjectEconomics, IVCU, Project } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

// --- Headers Helper ---
const getHeaders = () => {
    const token = localStorage.getItem('axiom_token');
    return {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {})
    };
};

export const ApiClient = {
    // --- Auth ---
    register: async (email: string, name: string, password: string): Promise<{ token: string; user: any }> => {
        const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, name, password })
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ error: "Registration failed" }));
            throw new Error(err.error || "Registration failed");
        }
        const data = await response.json();
        localStorage.setItem('axiom_token', data.token);
        localStorage.setItem('axiom_user_email', email);
        return data;
    },

    login: async (email: string, password: string): Promise<{ token: string; user: any }> => {
        const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ error: "Login failed" }));
            throw new Error(err.error || "Invalid credentials");
        }
        const data = await response.json();
        localStorage.setItem('axiom_token', data.token);
        localStorage.setItem('axiom_user_email', email);
        return data;
    },

    logout: () => {
        localStorage.removeItem('axiom_token');
        localStorage.removeItem('axiom_project_id');
        localStorage.removeItem('axiom_user_email');
    },

    isAuthenticated: (): boolean => {
        return !!localStorage.getItem('axiom_token');
    },

    // --- Generation & Intent ---
    parseIntent: async (intent: string, model?: string): Promise<any> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/intent/parse`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ intent, model })
            });
            if (!response.ok) throw new Error("Parse intent failed");
            return await response.json();
        } catch (e) {
            console.error("Parse Intent Error:", e);
            throw e;
        }
    },

    createIVCU: async (projectId: string, intent: string, sdo_id?: string): Promise<{ ivcu_id: string; status: string }> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/intent/create`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({
                    project_id: projectId,
                    raw_intent: intent,
                    sdo_id: sdo_id
                })
            });
            if (!response.ok) throw new Error("Create IVCU failed");
            return await response.json();
        } catch (e) {
            console.error("Create IVCU Error:", e);
            throw e;
        }
    },

    startGeneration: async (ivcuID: string, language: string = 'python', candidateCount: number = 3, strategy: string = 'simple'): Promise<{ generation_id: string; status: string }> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/generation/start`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({
                    ivcu_id: ivcuID,
                    language,
                    candidate_count: candidateCount,
                    strategy
                })
            });
            if (!response.ok) throw new Error("Start generation failed");
            return await response.json();
        } catch (e) {
            console.error("Start Generation Error:", e);
            throw e;
        }
    },

    getGenerationStatus: async (id: string): Promise<IVCU> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/generation/${id}/status`, {
                headers: getHeaders()
            });
            if (!response.ok) throw new Error("Get status failed");
            return await response.json();
        } catch (e) {
            console.error("Get Status Error:", e);
            throw e;
        }
    },

    cancelGeneration: async (id: string): Promise<boolean> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/generation/${id}/cancel`, {
                method: "POST",
                headers: getHeaders()
            });
            return response.ok;
        } catch (e) {
            console.error("Cancel Generation Error:", e);
            return false;
        }
    },

    snapshotState: async (sdoId: string): Promise<boolean> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/sdo/${sdoId}/snapshot`, {
                method: "POST",
                headers: getHeaders()
            });
            return response.ok;
        } catch (e) {
            console.error("Snapshot Error:", e);
            return false;
        }
    },

    getModels: async (tier?: string): Promise<any> => {
        try {
            const url = tier
                ? `${API_BASE}/api/v1/models?tier=${tier}`
                : `${API_BASE}/api/v1/models`;
            const response = await fetch(url, { headers: getHeaders() });
            if (!response.ok) throw new Error("Models fetch failed");
            return await response.json();
        } catch (e) {
            console.error("Get Models Error:", e);
            return { models: [], count: 0, cache_age_seconds: null };
        }
    },

    getDefaultModel: async (tier?: string): Promise<any> => {
        try {
            const url = tier
                ? `${API_BASE}/api/v1/models/default?tier=${tier}`
                : `${API_BASE}/api/v1/models/default`;
            const response = await fetch(url, { headers: getHeaders() });
            if (!response.ok) return null;
            return await response.json();
        } catch (e) {
            console.error("Get Default Model Error:", e);
            return null;
        }
    },

    getEstimatedCost: async (intent: string, model: string = "deepseek-v3"): Promise<{
        estimated_cost_usd: number;
        input_tokens: number;
        output_tokens: number;
        model: string;
    }> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/cost/estimate`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ intent, model })
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
    },

    getGraphData: async (): Promise<any> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/graph`, { headers: getHeaders() });
            if (!response.ok) throw new Error("Graph fetch failed");
            return await response.json();
        } catch (e) {
            console.error("Graph Data Error:", e);
            return { nodes: [], edges: [] };
        }
    },

    // --- Speculation ---
    speculateIntent: async (intent: string): Promise<SpeculationResult | null> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/speculate`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ intent })
            });
            if (!response.ok) throw new Error("Speculation failed");
            return await response.json();
        } catch (e) {
            console.error("Speculation Error:", e);
            return null;
        }
    },

    // --- Team Management ---
    getTeam: async (projectId: string): Promise<TeamMember[]> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/project/${projectId}/team`, {
                headers: getHeaders()
            });
            if (!response.ok) throw new Error("Fetch team failed");
            return await response.json();
        } catch (e) {
            console.error("Get Team Error:", e);
            return [];
        }
    },

    inviteMember: async (projectId: string, email: string, role: string): Promise<boolean> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/project/${projectId}/team/invite`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ email, role })
            });
            return response.ok;
        } catch (e) {
            console.error("Invite Member Error:", e);
            return false;
        }
    },

    removeMember: async (projectId: string, userId: string): Promise<boolean> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/project/${projectId}/team/${userId}`, {
                method: "DELETE",
                headers: getHeaders()
            });
            return response.ok;
        } catch (e) {
            console.error("Remove Member Error:", e);
            return false;
        }
    },

    // --- Economics ---
    // Note: We might need to add this endpoint to the backend if it doesn't exist yet
    getProjectEconomics: async (projectId: string): Promise<ProjectEconomics | null> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/project/${projectId}/economics`, {
                headers: getHeaders()
            });
            if (!response.ok) return null; // Endpoint might not exist yet
            return await response.json();
        } catch (e) {
            console.error("Economics Error:", e);
            return null;
        }
    },

    // --- Projects ---
    createProject: async (name: string): Promise<Project | null> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/projects`, {
                method: "POST",
                headers: getHeaders(),
                body: JSON.stringify({ name })
            });
            if (!response.ok) throw new Error("Create project failed");
            return await response.json();
        } catch (e) {
            console.error("Create Project Error:", e);
            return null;
        }
    },

    listProjects: async (): Promise<Project[]> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/projects`, {
                headers: getHeaders()
            });
            if (!response.ok) throw new Error("List projects failed");
            const data = await response.json();
            return data.projects || [];
        } catch (e) {
            console.error("List Projects Error:", e);
            return [];
        }
    },

    getProject: async (id: string): Promise<Project | null> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/projects/${id}`, {
                headers: getHeaders()
            });
            if (!response.ok) throw new Error("Get project failed");
            return await response.json();
        } catch (e) {
            console.error("Get Project Error:", e);
            return null;
        }
    },
    // --- Intelligence ---
    getReasoningTrace: async (ivcuId: string): Promise<any> => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/reasoning/${ivcuId}`, {
                headers: getHeaders()
            });
            if (!response.ok) throw new Error("Fetch reasoning trace failed");
            return await response.json();
        } catch (e) {
            console.error("Get Reasoning Trace Error:", e);
            return null;
        }
    }
};
