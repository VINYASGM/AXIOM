'use client';

import { useState } from 'react';
import { IntentCanvas } from '@/components/IntentCanvas';
import { ReasoningTracePanel } from '@/components/ReasoningTracePanel';
import { VerificationBreakdown } from '@/components/VerificationBreakdown';
import { useAxiomStore } from '@/store/axiom';
import { ProjectSelector } from '@/components/ProjectSelector';
import { TeamManagementDialog } from '@/components/TeamManagementDialog';

export default function Home() {
  const { currentIVCU } = useAxiomStore();
  const [isTeamDialogOpen, setIsTeamDialogOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#0f1117] text-gray-100 font-sans selection:bg-blue-500/30 overflow-hidden">
      <TeamManagementDialog isOpen={isTeamDialogOpen} onClose={() => setIsTeamDialogOpen(false)} />

      {/* Background Gradient */}
      <div className="fixed inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-[#0f1117] to-[#0f1117] pointer-events-none" />

      <main className="relative z-10 h-screen flex flex-col">
        {/* Header */}
        <header className="p-4 border-b border-white/5 bg-[#0f1117]/50 backdrop-blur-sm z-20">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 bg-clip-text text-transparent">
                  AXIOM
                </h1>
              </div>

              <div className="h-6 w-px bg-white/10" />

              <ProjectSelector onManageTeam={() => setIsTeamDialogOpen(true)} />
            </div>

            <div className="flex items-center gap-4">
              <span className="text-xs text-gray-500 font-mono hidden md:block">
                INTENT_VERIFIED_ENV
              </span>
            </div>
          </div>
        </header>

        {/* Main Content Area - Split Pane */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full max-w-7xl mx-auto flex">

            {/* Left Column: Canvas & Verification */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6">
              <section className="space-y-4">
                <IntentCanvas />
              </section>

              {/* Verification Results appear below the canvas when available */}
              {currentIVCU?.verificationResult && (
                <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <h3 className="text-sm font-semibold text-gray-400 mb-3 ml-1 uppercase tracking-wider">Verification Analysis</h3>
                  <VerificationBreakdown verificationResult={currentIVCU.verificationResult} />
                </section>
              )}
            </div>

            {/* Right Column: Reasoning Trace Sidebar */}
            <aside className="w-[400px] border-l border-white/5 bg-black/20 p-6 overflow-y-auto hidden lg:block">
              <ReasoningTracePanel />
            </aside>

          </div>
        </div>
      </main>
    </div>
  );
}
