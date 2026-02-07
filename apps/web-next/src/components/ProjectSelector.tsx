import { useState } from 'react';
import { ChevronDown, Plus, Settings, Users, Folder } from 'lucide-react';
import { useAxiomStore } from '@/store/axiom';
import { motion, AnimatePresence } from 'framer-motion';

interface ProjectSelectorProps {
    onManageTeam: () => void;
}

export function ProjectSelector({ onManageTeam }: ProjectSelectorProps) {
    const { currentProject, setCurrentProject } = useAxiomStore();
    const [isOpen, setIsOpen] = useState(false);

    // Mock projects for now
    const projects = [
        { id: '123e4567-e89b-12d3-a456-426614174000', name: 'Demo Project', security_context: 'public' },
        { id: '2', name: 'Axiom Core', security_context: 'confidential' },
        { id: '3', name: 'Frontend Refactor', security_context: 'internal' },
    ];

    return (
        <div className="relative z-40">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors group"
            >
                <div className="w-8 h-8 rounded bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm">
                    {currentProject?.name.charAt(0)}
                </div>
                <div className="text-left hidden md:block">
                    <div className="text-sm font-medium text-white flex items-center gap-2">
                        {currentProject?.name}
                        <ChevronDown className="w-3 h-3 text-gray-500 group-hover:text-white transition-colors" />
                    </div>
                </div>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        <div className="fixed inset-0" onClick={() => setIsOpen(false)} />
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            className="absolute top-full left-0 mt-2 w-64 bg-[#1a1d24] border border-white/10 rounded-xl shadow-2xl overflow-hidden"
                        >
                            <div className="p-2">
                                <div className="text-xs font-semibold text-gray-500 px-3 py-2 uppercase tracking-wider">Switch Project</div>
                                {projects.map((p) => (
                                    <button
                                        key={p.id}
                                        onClick={() => { setCurrentProject(p); setIsOpen(false); }}
                                        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 text-left transition-colors"
                                    >
                                        <Folder className="w-4 h-4 text-gray-400" />
                                        <span className={`text-sm ${currentProject?.id === p.id ? 'text-blue-400' : 'text-gray-300'}`}>
                                            {p.name}
                                        </span>
                                    </button>
                                ))}
                                <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 text-left transition-colors text-blue-400">
                                    <Plus className="w-4 h-4" />
                                    <span className="text-sm">Create New...</span>
                                </button>
                            </div>

                            <div className="border-t border-white/10 p-2">
                                <button
                                    onClick={() => { onManageTeam(); setIsOpen(false); }}
                                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 text-left transition-colors text-gray-300"
                                >
                                    <Users className="w-4 h-4" />
                                    <span className="text-sm">Manage Team</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5 text-left transition-colors text-gray-300">
                                    <Settings className="w-4 h-4" />
                                    <span className="text-sm">Settings</span>
                                </button>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
