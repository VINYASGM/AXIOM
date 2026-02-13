import React, { useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Zap,
  Terminal as TerminalIcon,
  Activity,
  Settings,
  Layers,
  Database,
  Globe,
  Radio,
  FlaskConical,
  CheckCircle2,
  Box,
  Users,
  LogOut
} from 'lucide-react';
import { IVCU, IVCUStatus } from './types';
import IntentCanvas from './components/IntentCanvas';
import ReviewPanel from './components/ReviewPanel';
import MemoryGraph from './components/MemoryGraph';
import Monitor from './components/Monitor';
import EconomicPanel from './components/EconomicPanel';
import Terminal from './components/Terminal';
import TestHub from './components/TestHub';
import AdaptiveScaffolding from './components/AdaptiveScaffolding';
import CounterfactualPanel from './components/CounterfactualPanel';
import TeamPanel from './components/TeamPanel';
import AuthScreen from './components/AuthScreen';
import ScrambleText from './components/ScrambleText';
import NavItem from './components/NavItem';
import TelemetryItem from './components/TelemetryItem';
import { ApiClient } from './lib/api';

type TabKey = 'canvas' | 'graph' | 'monitor' | 'tests' | 'team';

const App: React.FC = () => {
  const [authenticated, setAuthenticated] = useState(ApiClient.isAuthenticated());
  const [activeTab, setActiveTab] = useState<TabKey>('canvas');
  const [ivcuHistory, setIvcuHistory] = useState<IVCU[]>([]);
  const [currentIvcu, setCurrentIvcu] = useState<IVCU | null>(null);
  const [showCounterfactual, setShowCounterfactual] = useState(false);
  const [logs, setLogs] = useState<string[]>(["[SYSTEM] Axiom Core v2.5 Online", "[MEM] Neural Cache Initialized", "[AI] High-Fidelity Pipeline Synchronized", "[NODE] Cluster handshake achieved: 200 OK"]);

  const userEmail = typeof window !== 'undefined' ? localStorage.getItem('axiom_user_email') : null;
  const userInitial = userEmail ? userEmail[0].toUpperCase() : 'A';
  const projectId = typeof window !== 'undefined' ? localStorage.getItem('axiom_project_id') : null;

  const handleLogout = () => {
    ApiClient.logout();
    setAuthenticated(false);
  };

  const addLog = useCallback((msg: string) => {
    setLogs(prev => [...prev.slice(-49), msg]);
  }, []);

  const handleNewIvcu = (ivcu: IVCU) => {
    setCurrentIvcu(ivcu);
    if (ivcu.status === IVCUStatus.Verified || ivcu.status === IVCUStatus.Failed) {
      setIvcuHistory(prev => [ivcu, ...prev]);
    }
  };

  if (!authenticated) {
    return <AuthScreen onAuthenticated={() => setAuthenticated(true)} />;
  }

  const pageVariants = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
    exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
  };

  return (
    <div className="flex h-screen bg-[#010204] overflow-hidden text-slate-200 selection:bg-sky-500/25">

      <div className="flex-1 flex overflow-hidden">
        {/* === Sidebar === */}
        <nav className="w-16 glass border-r border-white/5 flex flex-col items-center py-4 z-50 bg-black/50 shadow-2xl">
          {/* Logo */}
          <div className="p-3 bg-gradient-to-br from-sky-500 to-sky-700 rounded-2xl text-white shadow-[0_0_25px_rgba(14,165,233,0.3)] cursor-pointer mb-6 relative group">
            <Box size={20} />
            <div className="absolute inset-0 rounded-2xl bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>

          {/* Nav Items */}
          <div className="flex-1 flex flex-col space-y-3">
            <NavItem active={activeTab === 'canvas'} onClick={() => setActiveTab('canvas')} icon={<Layers size={20} />} label="Intent Canvas" />
            <NavItem active={activeTab === 'graph'} onClick={() => setActiveTab('graph')} icon={<Database size={20} />} label="Memory Graph" />
            <NavItem active={activeTab === 'monitor'} onClick={() => setActiveTab('monitor')} icon={<Activity size={20} />} label="Health Monitor" />
            <NavItem active={activeTab === 'tests'} onClick={() => setActiveTab('tests')} icon={<FlaskConical size={20} />} label="Test Suite" />
            <NavItem active={activeTab === 'team'} onClick={() => setActiveTab('team')} icon={<Users size={20} />} label="Team Access" />
          </div>

          {/* Bottom Nav */}
          <div className="mt-auto space-y-2 pb-3">
            <NavItem active={false} icon={<Globe size={18} />} label="Network" />
            <NavItem active={false} icon={<Settings size={18} />} label="System Config" />
            <div className="w-8 h-px bg-white/5 my-2" />
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400 text-xs font-bold">
                {userInitial}
              </div>
              <button
                onClick={handleLogout}
                className="group p-2 rounded-xl text-slate-700 hover:text-red-400 hover:bg-red-500/10 transition-all duration-300"
                title="Logout"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </nav>

        {/* === Main Area === */}
        <main className="flex-1 flex flex-col relative overflow-hidden">

          {/* Header */}
          <header className="h-14 glass border-b border-white/10 flex items-center justify-between px-6 z-40 bg-black/40 shadow-xl shrink-0">
            <div className="flex items-center space-x-4">
              <h1 className="text-lg font-black tracking-tight text-white flex items-center gap-3">
                <ScrambleText text="AXIOM" className="text-xl" />
                <span className="text-[9px] font-bold mono px-2.5 py-1 bg-sky-500/10 text-sky-400 rounded-lg border border-sky-500/20 uppercase tracking-[0.3em] flex items-center gap-2 shadow-[inset_0_0_12px_rgba(14,165,233,0.05)]">
                  <span className="w-1.5 h-1.5 bg-sky-400 rounded-full shadow-[0_0_10px_#0ea5e9]" />
                  SYNCED
                </span>
              </h1>
              <div className="hidden md:flex items-center space-x-4 ml-4">
                <div className="flex items-center space-x-2 group cursor-default">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-700 group-hover:bg-sky-500 transition-colors" />
                  <span className="text-[9px] text-slate-600 mono uppercase tracking-[0.2em] font-medium">US_EAST_1D</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Radio size={12} className="text-emerald-500 animate-pulse" />
                  <span className="text-[9px] text-slate-600 mono uppercase tracking-[0.2em] font-medium">Secure</span>
                </div>
              </div>
            </div>

            <EconomicPanel />
          </header>

          {/* Content + Telemetry */}
          <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">

            {/* Dynamic Viewport */}
            <div className="flex-1 overflow-y-auto p-4 lg:p-6 custom-scroll bg-gradient-to-b from-transparent to-black/40">
              <AnimatePresence mode="wait">
                {activeTab === 'canvas' && (
                  <motion.div key="canvas" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="max-w-7xl mx-auto space-y-6 pb-16">
                    <AdaptiveScaffolding>
                      {(level, skills) => (
                        <IntentCanvas
                          onGenerated={handleNewIvcu}
                          addLog={addLog}
                          scaffoldingLevel={level}
                          userSkills={skills}
                        />
                      )}
                    </AdaptiveScaffolding>

                    {currentIvcu && (
                      <div className="transform transition-all duration-500">
                        <ReviewPanel
                          ivcu={currentIvcu}
                          onExplore={() => setShowCounterfactual(true)}
                        />
                      </div>
                    )}

                    {showCounterfactual && currentIvcu && (
                      <CounterfactualPanel
                        baseIvcu={currentIvcu}
                        onClose={() => setShowCounterfactual(false)}
                        onApply={(newIvcu) => {
                          setCurrentIvcu(newIvcu);
                          setShowCounterfactual(false);
                          addLog(`COUNTERFACTUAL: Variant applied. ID: ${newIvcu.id}`);
                        }}
                      />
                    )}
                  </motion.div>
                )}

                {activeTab === 'graph' && (
                  <motion.div key="graph" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full w-full p-2">
                    <MemoryGraph />
                  </motion.div>
                )}

                {activeTab === 'monitor' && (
                  <motion.div key="monitor" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full p-2">
                    <Monitor history={ivcuHistory} />
                  </motion.div>
                )}

                {activeTab === 'tests' && (
                  <motion.div key="tests" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full p-2">
                    <TestHub />
                  </motion.div>
                )}

                {activeTab === 'team' && (
                  <motion.div key="team" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full p-2 max-w-4xl mx-auto">
                    <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                      <Users className="text-sky-400" size={20} />
                      Project Team
                    </h2>
                    <TeamPanel projectId={projectId || 'default-project'} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Telemetry Sidebar */}
            <aside className="w-[380px] glass border-l border-white/5 flex flex-col hidden xl:flex z-40 bg-black/70 shadow-4xl relative">
              <div className="absolute inset-0 bg-gradient-to-b from-sky-500/[0.02] to-transparent pointer-events-none" />

              {/* Telemetry Header */}
              <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between bg-white/[0.01]">
                <div className="flex items-center space-x-3">
                  <TerminalIcon size={16} className="text-sky-400 bloom" />
                  <span className="text-[10px] font-bold uppercase tracking-[0.4em] text-slate-300 mono">Telemetry</span>
                </div>
                <div className="px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[9px] mono text-emerald-400 font-bold tracking-widest shadow-sm shadow-emerald-500/5">
                  LIVE
                </div>
              </div>

              {/* Terminal */}
              <div className="flex-1 overflow-hidden flex flex-col">
                <Terminal logs={logs} />
              </div>

              {/* Stats Footer */}
              <div className="p-4 bg-black/50 border-t border-white/10 space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center px-1">
                    <h4 className="text-[10px] font-bold text-slate-600 uppercase tracking-[0.3em] mono">Neural Integrity</h4>
                    <span className="text-[10px] text-sky-400 font-bold mono bloom">99.1%</span>
                  </div>
                  <div className="space-y-2.5">
                    <TelemetryItem label="Memory" value="0.08 GB" color="text-sky-400" icon={<Activity size={14} />} />
                    <TelemetryItem label="Engine" value="Optimized" color="text-emerald-400" icon={<CheckCircle2 size={14} />} />
                    <TelemetryItem label="Rate" value="2.1 GB/s" color="text-slate-100" icon={<Zap size={14} />} />
                  </div>
                </div>

                {/* Uptime Card */}
                <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/10 space-y-2.5 relative overflow-hidden group shadow-inner">
                  <div className="absolute inset-0 bg-gradient-to-tr from-sky-500/15 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-1000" />
                  <div className="flex justify-between items-center relative z-10">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] mono">Uptime</span>
                    <span className="text-sm font-mono text-slate-200 font-bold tracking-tighter">1,288.4H</span>
                  </div>
                  <div className="w-full bg-black/60 h-2 rounded-full overflow-hidden border border-white/10 relative z-10 p-[1px]">
                    <div className="bg-sky-500 h-full rounded-full shadow-[0_0_15px_#0ea5e9] w-[98.2%]" />
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
