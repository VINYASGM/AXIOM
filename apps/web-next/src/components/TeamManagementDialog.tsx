'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserPlus, Trash2, Shield, ShieldAlert, User } from 'lucide-react';
import { useTeamStore } from '@/store/team';
import { useAxiomStore } from '@/store/axiom';

interface TeamManagementDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export function TeamManagementDialog({ isOpen, onClose }: TeamManagementDialogProps) {
    const { currentProject } = useAxiomStore();
    const { members, fetchMembers, inviteMember, removeMember, isLoading } = useTeamStore();

    const [email, setEmail] = useState('');
    const [role, setRole] = useState<'viewer' | 'editor' | 'admin'>('viewer');

    useEffect(() => {
        if (isOpen && currentProject) {
            fetchMembers(currentProject.id);
        }
    }, [isOpen, currentProject, fetchMembers]);

    const handleInvite = async () => {
        if (!email || !currentProject) return;
        await inviteMember(currentProject.id, email, role);
        setEmail('');
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl bg-[#0f1117] border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
                    >
                        <div className="flex items-center justify-between p-6 border-b border-white/10">
                            <div>
                                <h2 className="text-xl font-bold text-white mb-1">Team Management</h2>
                                <p className="text-sm text-gray-400">Manage access to {currentProject?.name}</p>
                            </div>
                            <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="p-6 space-y-8">
                            {/* Invite Section */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">Invite Member</h3>
                                <div className="flex gap-3">
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="colleague@company.com"
                                        className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    />
                                    <select
                                        value={role}
                                        onChange={(e) => setRole(e.target.value as any)}
                                        className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    >
                                        <option value="viewer">Viewer</option>
                                        <option value="editor">Editor</option>
                                        <option value="admin">Admin</option>
                                    </select>
                                    <button
                                        onClick={handleInvite}
                                        disabled={!email}
                                        className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
                                    >
                                        <UserPlus className="w-4 h-4" />
                                        Invite
                                    </button>
                                </div>
                            </div>

                            {/* Members List */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">Members ({members.length})</h3>
                                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                    {isLoading ? (
                                        <div className="text-center py-8 text-gray-500">Loading members...</div>
                                    ) : members.map((member) => (
                                        <div key={member.id} className="flex items-center justify-between bg-white/5 rounded-lg p-3 border border-white/5 hover:border-white/10 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                                                    {member.name.charAt(0)}
                                                </div>
                                                <div>
                                                    <div className="font-medium text-white">{member.name}</div>
                                                    <div className="text-xs text-gray-400">{member.email}</div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <span className={`px-2 py-1 rounded text-xs font-medium border ${member.role === 'admin' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                                                    member.role === 'editor' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                                        'bg-gray-500/10 text-gray-400 border-gray-500/20'
                                                    }`}>
                                                    {member.role}
                                                </span>
                                                <button
                                                    onClick={() => currentProject && removeMember(currentProject.id, member.id)}
                                                    className="p-2 text-gray-500 hover:text-red-400 transition-colors"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
