
import { ModelTier, TeamMember, SpeculationResult, ProjectEconomics } from '../types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// --- Headers Helper ---
const getHeaders = () => {
    const token = localStorage.getItem('axiom_token');
    return {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {})
    };
};

export const ApiClient = {
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
    }
};
