'use client';

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Search, Wifi } from 'lucide-react';

interface AppShellProps {
    children: ReactNode;
}

export function AppShell({ children }: { children: ReactNode }) {
    return (
        <div className="flex h-screen bg-canvas overflow-hidden font-sans text-primary selection:bg-axiom-500/30">
            {/* Left Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Top Bar (Global Context) */}
                <header className="h-14 border-b border-white/5 bg-surface/30 backdrop-blur-sm flex items-center justify-between px-6 shrink-0 z-10">
                    {/* Breadcrumbs / Context (Placeholder) */}
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span className="text-gray-300">axiome-corp</span>
                        <span>/</span>
                        <span className="text-white">default-project</span>
                    </div>

                    {/* Right Actions */}
                    <div className="flex items-center gap-4">
                        {/* Command Palette Trigger */}
                        <button className="flex items-center gap-2 px-3 py-1.5 bg-element/50 border border-white/5 rounded-lg text-xs text-gray-400 hover:text-white hover:border-white/10 transition-all group">
                            <Search className="w-3 h-3 group-hover:text-axiom-400 transition-colors" />
                            <span>Search...</span>
                            <kbd className="hidden sm:inline-block px-1.5 bg-black/20 rounded border border-white/5 font-mono text-[10px] text-gray-500">Ctrl K</kbd>
                        </button>

                        {/* Environment & Connection */}
                        <div className="h-4 w-px bg-white/10 mx-1" />

                        <div className="flex items-center gap-2 px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-medium text-emerald-400">
                            <Wifi className="w-3 h-3" />
                            <span>CONNECTED</span>
                        </div>
                    </div>
                </header>

                {/* Content Viewport */}
                <main className="flex-1 overflow-hidden relative">
                    {children}
                </main>
            </div>
        </div>
    );
}
