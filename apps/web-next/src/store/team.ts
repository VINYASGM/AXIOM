import { create } from 'zustand';
import { useAxiomStore } from './axiom';

export interface TeamMember {
    id: string;
    name: string;
    email: string;
    role: 'viewer' | 'editor' | 'admin';
    added_at: string;
}

interface TeamState {
    members: TeamMember[];
    isLoading: boolean;
    error: string | null;

    fetchMembers: (projectId: string) => Promise<void>;
    inviteMember: (projectId: string, email: string, role: TeamMember['role']) => Promise<void>;
    removeMember: (projectId: string, userId: string) => Promise<void>;
}

export const useTeamStore = create<TeamState>((set) => ({
    members: [],
    isLoading: false,
    error: null,

    fetchMembers: async (projectId: string) => {
        set({ isLoading: true, error: null });
        const token = useAxiomStore.getState().token;
        if (!token) {
            // Mock data for dev without auth
            set({
                members: [
                    { id: '1', name: 'Alice Admin', email: 'alice@axiom.co', role: 'admin', added_at: new Date().toISOString() },
                    { id: '2', name: 'Bob Builder', email: 'bob@axiom.co', role: 'editor', added_at: new Date().toISOString() },
                ],
                isLoading: false
            });
            return;
        }

        try {
            const res = await fetch(`/api/v1/project/${projectId}/team`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                set({ members: data.members || [] });
            } else {
                set({ error: 'Failed to fetch members' });
            }
        } catch (err) {
            set({ error: 'Network error' });
        } finally {
            set({ isLoading: false });
        }
    },

    inviteMember: async (projectId, email, role) => {
        const token = useAxiomStore.getState().token;
        if (!token) {
            // Mock add
            set(state => ({
                members: [...state.members, {
                    id: Math.random().toString(),
                    name: email.split('@')[0],
                    email,
                    role,
                    added_at: new Date().toISOString()
                }]
            }));
            return;
        }

        try {
            const res = await fetch(`/api/v1/project/${projectId}/team/invite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ email, role })
            });

            if (res.ok) {
                // Refresh list
                useTeamStore.getState().fetchMembers(projectId);
            }
        } catch (err) {
            console.error(err);
        }
    },

    removeMember: async (projectId, userId) => {
        const token = useAxiomStore.getState().token;
        if (!token) {
            set(state => ({
                members: state.members.filter(m => m.id !== userId)
            }));
            return;
        }

        try {
            await fetch(`/api/v1/project/${projectId}/team/${userId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            // Optimistic update
            set(state => ({
                members: state.members.filter(m => m.id !== userId)
            }));
        } catch (err) {
            console.error(err);
        }
    }
}));
