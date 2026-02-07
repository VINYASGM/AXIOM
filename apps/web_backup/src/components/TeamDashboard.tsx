'use client';

import { useState, useEffect } from 'react';
import { useAxiomStore } from '@/store/axiom';
import { Users, UserPlus, Trash2, Shield, MoreVertical } from 'lucide-react';

interface Member {
    id: string;
    name: string;
    email: string;
    role: 'admin' | 'editor' | 'viewer';
    added_at: string;
}

export function TeamDashboard() {
    const { currentProject } = useAxiomStore();
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(false);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('viewer');
    const [isInviting, setIsInviting] = useState(false);

    useEffect(() => {
        if (currentProject?.id) {
            fetchMembers();
        }
    }, [currentProject?.id]);

    const fetchMembers = async () => {
        if (!currentProject?.id) return;
        setLoading(true);
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/project/${currentProject.id}/team`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}` // rudimentary auth check
                }
            });
            if (res.ok) {
                const data = await res.json();
                setMembers(data.members || []);
            }
        } catch (error) {
            console.error('Failed to fetch members', error);
        } finally {
            setLoading(false);
        }
    };

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!currentProject?.id) return;

        setIsInviting(true);
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/project/${currentProject.id}/team/invite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ email: inviteEmail, role: inviteRole })
            });

            if (res.ok) {
                setInviteEmail('');
                fetchMembers();
            } else {
                alert('Failed to invite user');
            }
        } catch (error) {
            console.error('Error inviting user', error);
        } finally {
            setIsInviting(false);
        }
    };

    const handleRemove = async (userId: string) => {
        if (!confirm('Are you sure you want to remove this user?')) return;
        if (!currentProject?.id) return;

        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/project/${currentProject.id}/team/${userId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (res.ok) {
                fetchMembers();
            }
        } catch (error) {
            console.error('Error removing user', error);
        }
    };

    if (!currentProject) {
        return <div className="text-gray-500 text-center py-8">Select a project to manage team.</div>;
    }

    return (
        <div className="bg-black/40 border border-white/5 rounded-xl p-6 max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                        <Users className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-white">Team Members</h2>
                        <p className="text-sm text-gray-400">Manage access to {currentProject.name}</p>
                    </div>
                </div>
                <div className="text-xs text-gray-500">
                    {members.length} member{members.length !== 1 ? 's' : ''}
                </div>
            </div>

            {/* Invite Form */}
            <form onSubmit={handleInvite} className="mb-8 bg-white/5 rounded-lg p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-400 mb-1">Email Address</label>
                    <input
                        type="email"
                        required
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="colleague@example.com"
                        className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
                    />
                </div>
                <div className="w-32">
                    <label className="block text-xs font-medium text-gray-400 mb-1">Role</label>
                    <select
                        value={inviteRole}
                        onChange={(e) => setInviteRole(e.target.value)}
                        className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
                    >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <button
                    type="submit"
                    disabled={isInviting}
                    className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm font-medium flex items-center gap-2"
                >
                    <UserPlus className="w-4 h-4" />
                    Invite
                </button>
            </form>

            {/* Members List */}
            <div className="space-y-2">
                {loading ? (
                    <div className="text-center py-8 text-gray-500">Loading members...</div>
                ) : members.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">No members found</div>
                ) : (
                    members.map(member => (
                        <div key={member.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5 hover:border-white/10 transition-colors">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center text-xs font-medium text-white border border-white/10">
                                    {member.name ? member.name.charAt(0).toUpperCase() : member.email.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-white">{member.name || member.email}</div>
                                    <div className="text-xs text-gray-500">{member.email}</div>
                                </div>
                            </div>

                            <div className="flex items-center gap-4">
                                <span className={`text-xs px-2 py-0.5 rounded border ${member.role === 'admin' ? 'bg-purple-500/10 border-purple-500/20 text-purple-400' :
                                        member.role === 'editor' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' :
                                            'bg-gray-500/10 border-gray-500/20 text-gray-400'
                                    }`}>
                                    {member.role.toUpperCase()}
                                </span>

                                <button
                                    onClick={() => handleRemove(member.id)}
                                    className="p-1.5 text-gray-500 hover:text-red-400 transition-colors rounded hover:bg-white/5"
                                    title="Remove member"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
