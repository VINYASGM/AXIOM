
import React, { useState, useEffect } from 'react';
import { Users, UserPlus, Shield, X, Check } from 'lucide-react';
import { TeamMember } from '../types';
import { ApiClient } from '../lib/api';

interface TeamPanelProps {
    projectId: string;
}

const TeamPanel: React.FC<TeamPanelProps> = ({ projectId }) => {
    const [members, setMembers] = useState<TeamMember[]>([]);
    const [loading, setLoading] = useState(true);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('viewer');
    const [isInviting, setIsInviting] = useState(false);

    useEffect(() => {
        loadTeam();
    }, [projectId]);

    const loadTeam = async () => {
        setLoading(true);
        const team = await ApiClient.getTeam(projectId);
        setMembers(team || []);
        setLoading(false);
    };

    const handleInvite = async () => {
        if (!inviteEmail) return;
        setIsInviting(true);
        const success = await ApiClient.inviteMember(projectId, inviteEmail, inviteRole);
        if (success) {
            setInviteEmail('');
            loadTeam(); // Reload list
        }
        setIsInviting(false);
    };

    const handleRemove = async (userId: string) => {
        if (confirm('Remove user from project?')) {
            const success = await ApiClient.removeMember(projectId, userId);
            if (success) loadTeam();
        }
    };

    return (
        <div className="p-6 glass rounded-3xl border border-white/10 space-y-6">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                    <Users size={20} className="text-sky-400" />
                    Team Access
                </h3>
                <span className="text-xs text-slate-500 uppercase tracking-widest font-mono">
                    {members.length} Members
                </span>
            </div>

            {/* Invite Form */}
            <div className="flex gap-2">
                <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@axiom.dev"
                    className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500/50"
                />
                <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-400 focus:outline-none"
                >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                </select>
                <button
                    onClick={handleInvite}
                    disabled={isInviting || !inviteEmail}
                    className="p-2 bg-sky-500/20 hover:bg-sky-500/30 text-sky-400 rounded-xl transition-colors disabled:opacity-50"
                >
                    {isInviting ? <div className="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" /> : <UserPlus size={20} />}
                </button>
            </div>

            {/* Member List */}
            <div className="space-y-3">
                {loading ? (
                    <div className="text-center py-4 text-slate-600 animate-pulse">Loading directory...</div>
                ) : members.length === 0 ? (
                    <div className="text-center py-4 text-slate-600">No members found.</div>
                ) : (
                    members.map((member) => (
                        <div key={member.id} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5 group">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-xs font-bold text-slate-300">
                                    {member.email.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-slate-300">{member.email}</div>
                                    <div className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1">
                                        <Shield size={10} className={member.role === 'admin' || member.role === 'owner' ? 'text-emerald-400' : 'text-slate-600'} />
                                        {member.role}
                                    </div>
                                </div>
                            </div>

                            {/* Actions (Only show if not self? For now showing all) */}
                            <button
                                onClick={() => handleRemove(member.id)}
                                className="p-1.5 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default TeamPanel;
