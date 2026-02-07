'use client';

import { usePathname, useRouter } from 'next/navigation';
import { Sparkles, Activity, History, Settings, LogOut, User } from 'lucide-react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

const NAV_ITEMS = [
    { id: 'intent', icon: Sparkles, label: 'Intent Studio', path: '/intent' },
    { id: 'monitor', icon: Activity, label: 'Trust & Verification', path: '/monitor' },
    { id: 'history', icon: History, label: 'Genealogy', path: '/history' },
    { id: 'admin', icon: Settings, label: 'Organization', path: '/admin' },
];

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();

    return (
        <div className="w-64 h-screen bg-surface border-r border-white/5 flex flex-col justify-between p-4">
            {/* Logo area */}
            <div className="flex items-center gap-3 px-2 mb-8 mt-2">
                <div className="w-8 h-8 rounded-lg bg-axiom-500 flex items-center justify-center text-white font-bold shadow-lg shadow-axiom-500/20">
                    A
                </div>
                <div>
                    <h1 className="font-semibold text-white tracking-wide">AXIOM</h1>
                    <p className="text-[10px] text-gray-500 font-mono tracking-wider">ENTERPRISE</p>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1">
                {NAV_ITEMS.map((item) => {
                    const isActive = pathname.startsWith(item.path);
                    const Icon = item.icon;

                    return (
                        <button
                            key={item.id}
                            onClick={() => router.push(item.path)}
                            className={clsx(
                                "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group relative",
                                isActive
                                    ? "text-white bg-white/5"
                                    : "text-gray-400 hover:text-white hover:bg-white/5"
                            )}
                        >
                            <Icon className={clsx("w-4 h-4", isActive ? "text-axiom-400" : "text-gray-500 group-hover:text-gray-400")} />
                            <span>{item.label}</span>

                            {isActive && (
                                <motion.div
                                    layoutId="activeNav"
                                    className="absolute left-0 w-0.5 h-6 bg-axiom-500 rounded-r-full"
                                />
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* User Profile */}
            <div className="pt-4 border-t border-white/5">
                <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 cursor-pointer group transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-axiom-400 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
                        V
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <p className="text-sm text-white truncate group-hover:text-axiom-300 transition-colors">Vinyas G M</p>
                        <p className="text-[10px] text-gray-500 truncate">Owner • AXIOM Corp</p>
                    </div>
                    <LogOut className="w-4 h-4 text-gray-600 hover:text-red-400 transition-colors" />
                </div>
            </div>
        </div>
    );
}
