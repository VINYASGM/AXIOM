
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence, LayoutGroup, useMotionValue, useSpring, useTransform } from 'framer-motion';
import {
    Zap,
    Terminal as TerminalIcon,
    Cpu,
    ShieldCheck,
    Database,
    Activity,
    Settings,
    Layers,
    ChevronRight,
    Code2,
    CheckCircle2,
    AlertCircle,
    Menu,
    Globe,
    Radio,
    ExternalLink,
    FlaskConical,
    Eye,
    Lock,
    Box,
    Layers3
} from 'lucide-react';
import { IVCU, IVCUStatus, ModelTier } from './types';
import IntentCanvas from './components/IntentCanvas';
import ReviewPanel from './components/ReviewPanel';
import MemoryGraph from './components/MemoryGraph';
import Monitor from './components/Monitor';
import EconomicPanel from './components/EconomicPanel';
import Terminal from './components/Terminal';
import TestHub from './components/TestHub';

// --- Kinetic UI Elements ---

const ScrambleText: React.FC<{ text: string, className?: string, duration?: number }> = ({ text, className, duration = 1 }) => {
    const [display, setDisplay] = useState(text);
    const chars = "!<>-_\\/[]{}—=+*^?#________";

    useEffect(() => {
        let iteration = 0;
        const interval = setInterval(() => {
            setDisplay(
                text.split("")
                    .map((char, index) => {
                        if (index < iteration) return text[index];
                        return chars[Math.floor(Math.random() * chars.length)];
                    })
                    .join("")
            );
            if (iteration >= text.length) clearInterval(interval);
            iteration += 1 / (duration * 20); // Faster scramble
        }, 40);
        return () => clearInterval(interval);
    }, [text, duration]);

    return <span className={className}>{display}</span>;
};

const BackgroundVisuals: React.FC = () => {
    return (
        <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
            {/* Floating Geometric Orbs */}
            {[...Array(10)].map((_, i) => (
                <motion.div
                    key={i}
                    className="absolute rounded-full border border-white/5 bg-gradient-to-br from-sky-500/10 to-transparent blur-3xl"
                    initial={{
                        width: Math.random() * 600 + 200,
                        height: Math.random() * 600 + 200,
                        x: Math.random() * 100 + "%",
                        y: Math.random() * 100 + "%",
                        opacity: 0.05
                    }}
                    animate={{
                        x: [Math.random() * 100 + "%", Math.random() * 100 + "%"],
                        y: [Math.random() * 100 + "%", Math.random() * 100 + "%"],
                        scale: [1, 1.3, 1],
                        opacity: [0.05, 0.1, 0.05]
                    }}
                    transition={{
                        duration: Math.random() * 30 + 25,
                        repeat: Infinity,
                        ease: "linear"
                    }}
                />
            ))}
        </div>
    );
};

const BootSequence: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
    return (
        <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.15, filter: 'blur(60px)' }}
            transition={{ duration: 1.5, ease: "circIn" }}
            className="fixed inset-0 z-[9999] bg-[#010204] flex flex-col items-center justify-center p-12 overflow-hidden"
        >
            <div className="max-w-2xl w-full space-y-12 relative">
                <div className="space-y-8">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: "100%" }}
                        transition={{ duration: 1.4, ease: "circOut" }}
                        className="h-px bg-gradient-to-r from-transparent via-sky-500/60 to-transparent"
                    />
                    <div className="flex justify-between items-end">
                        <div className="space-y-4">
                            <span className="text-[11px] mono text-slate-500 block tracking-[0.6em] uppercase">Kernel Interface 0x9A2F</span>
                            <h1 className="text-6xl font-black tracking-tighter text-white">AXIOM <span className="text-sky-500 bloom">CORE</span></h1>
                        </div>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex items-center space-x-4 text-[10px] mono text-emerald-500 font-bold bg-emerald-500/10 px-5 py-2 rounded-full border border-emerald-500/20 shadow-lg shadow-emerald-500/5"
                        >
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="tracking-widest">SEMANTIC_LINK: ACTIVE</span>
                        </motion.div>
                    </div>
                </div>

                <div className="glass border border-white/10 p-10 rounded-[3rem] space-y-8 font-mono text-[12px] bg-black/60 shadow-3xl">
                    <div className="space-y-3 text-slate-500">
                        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>> [0.0001] Initializing quantum logic gates...</motion.p>
                        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>> [0.0004] Mapping neural semantic weights (Tier 9)...</motion.p>
                        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>> [0.0010] Synchronizing persistent memory mesh...</motion.p>
                        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }} className="text-sky-400 font-bold">> [0.0015] AXIOM_READY: Handshake established.</motion.p>
                    </div>

                    <div className="relative h-2 bg-slate-900 rounded-full overflow-hidden border border-white/5 shadow-inner">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: "100%" }}
                            transition={{ duration: 2.8, ease: "circInOut" }}
                            onAnimationComplete={onComplete}
                            className="absolute top-0 left-0 h-full bg-sky-500 shadow-[0_0_30px_#0ea5e9]"
                        />
                    </div>
                </div>
            </div>

            <motion.div
                animate={{ opacity: [0, 0.03, 0] }}
                transition={{ duration: 0.08, repeat: Infinity, repeatDelay: 1.5 }}
                className="absolute inset-0 bg-sky-500 z-[-1]"
            />
        </motion.div>
    );
};

const App: React.FC = () => {
    const [booting, setBooting] = useState(true);
    const [activeTab, setActiveTab] = useState<'canvas' | 'graph' | 'monitor' | 'tests'>('canvas');
    const [ivcuHistory, setIvcuHistory] = useState<IVCU[]>([]);
    const [currentIvcu, setCurrentIvcu] = useState<IVCU | null>(null);
    const [logs, setLogs] = useState<string[]>(["[SYSTEM] Axiom Core v2.5 Online", "[MEM] Neural Cache Initialized", "[AI] High-Fidelity Pipeline Synchronized", "[NODE] Cluster handshake achieved: 200 OK"]);

    // Global Parallax Control
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);
    const springConfig = { damping: 50, stiffness: 100 };
    const rotateX = useSpring(useTransform(mouseY, [-600, 600], [2, -2]), springConfig);
    const rotateY = useSpring(useTransform(mouseX, [-600, 600], [-2, 2]), springConfig);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            mouseX.set(e.clientX - window.innerWidth / 2);
            mouseY.set(e.clientY - window.innerHeight / 2);
        };
        window.addEventListener('mousemove', handleMouseMove);
        return () => window.removeEventListener('mousemove', handleMouseMove);
    }, [mouseX, mouseY]);

    const addLog = useCallback((msg: string) => {
        setLogs(prev => [...prev.slice(-49), msg]);
    }, []);

    const handleNewIvcu = (ivcu: IVCU) => {
        setCurrentIvcu(ivcu);
        if (ivcu.status === IVCUStatus.Verified || ivcu.status === IVCUStatus.Failed) {
            setIvcuHistory(prev => [ivcu, ...prev]);
        }
    };

    return (
        <div className="flex h-screen bg-[#010204] overflow-hidden text-slate-200 selection:bg-sky-500/25">
            <AnimatePresence>
                {booting && <BootSequence onComplete={() => setBooting(false)} />}
            </AnimatePresence>

            <BackgroundVisuals />

            <motion.div
                style={{ rotateX, rotateY }}
                className="flex-1 flex overflow-hidden perspective-2000"
            >
                {/* Cinematic Sidebar */}
                <nav className="w-32 glass border-r border-white/5 flex flex-col items-center py-16 space-y-16 z-50 bg-black/50 shadow-2xl">
                    <motion.div
                        whileHover={{ scale: 1.1, rotate: 180 }}
                        whileTap={{ scale: 0.9 }}
                        transition={{ type: "spring", stiffness: 400 }}
                        className="p-6.5 bg-gradient-to-br from-sky-500 to-sky-700 rounded-[2.8rem] text-white shadow-[0_0_40px_rgba(14,165,233,0.35)] cursor-pointer mb-12 relative group"
                    >
                        <Box size={30} />
                        <motion.div className="absolute inset-0 rounded-[2.8rem] bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </motion.div>

                    <div className="flex-1 flex flex-col space-y-14">
                        <NavItem active={activeTab === 'canvas'} onClick={() => setActiveTab('canvas')} icon={<Layers size={26} />} label="Intent Canvas" />
                        <NavItem active={activeTab === 'graph'} onClick={() => setActiveTab('graph')} icon={<Database size={26} />} label="Memory Graph" />
                        <NavItem active={activeTab === 'monitor'} onClick={() => setActiveTab('monitor')} icon={<Activity size={26} />} label="Health Monitor" />
                        <NavItem active={activeTab === 'tests'} onClick={() => setActiveTab('tests')} icon={<FlaskConical size={26} />} label="Test Suite" />
                    </div>

                    <div className="mt-auto space-y-12 pb-12">
                        <NavItem active={false} icon={<Globe size={24} />} label="Network" />
                        <NavItem active={false} icon={<Settings size={24} />} label="System Config" />
                    </div>
                </nav>

                {/* Global HUD Layout */}
                <main className="flex-1 flex flex-col relative overflow-hidden">
                    <header className="h-36 glass border-b border-white/10 flex items-center justify-between px-20 z-40 bg-black/40 shadow-xl">
                        <div className="flex items-center space-x-16">
                            <div className="flex flex-col">
                                <h1 className="text-5xl font-black tracking-tight text-white flex items-center gap-10">
                                    <ScrambleText text="AXIOM" />
                                    <span className="text-[11px] font-bold mono px-10 py-3.5 bg-sky-500/10 text-sky-400 rounded-2xl border border-sky-500/20 uppercase tracking-[0.5em] flex items-center gap-6 shadow-[inset_0_0_20px_rgba(14,165,233,0.05)]">
                                        <motion.span
                                            animate={{ scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
                                            transition={{ duration: 2.5, repeat: Infinity }}
                                            className="w-3 h-3 bg-sky-400 rounded-full shadow-[0_0_20px_#0ea5e9]"
                                        />
                                        NEURAL_SYNC_OPTIMIZED
                                    </span>
                                </h1>
                                <div className="flex items-center space-x-12 mt-6">
                                    <div className="flex items-center space-x-4 group cursor-default">
                                        <div className="w-2 h-2 rounded-full bg-slate-700 group-hover:bg-sky-500 transition-colors shadow-lg" />
                                        <span className="text-[10px] text-slate-500 mono uppercase tracking-[0.3em] font-medium">CLUSTER_US_EAST_1D</span>
                                    </div>
                                    <div className="flex items-center space-x-4">
                                        <Radio size={16} className="text-emerald-500 animate-pulse" />
                                        <span className="text-[10px] text-slate-600 mono uppercase tracking-[0.3em] font-medium">Semantic Stream: Secure</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <EconomicPanel />
                    </header>

                    <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
                        {/* Dynamic Viewport */}
                        <div className="flex-1 overflow-y-auto p-12 lg:p-24 custom-scroll bg-gradient-to-b from-transparent to-black/40">
                            <AnimatePresence mode="wait">
                                {activeTab === 'canvas' && (
                                    <motion.div
                                        key="canvas"
                                        initial={{ opacity: 0, y: 50, filter: 'blur(20px)' }}
                                        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                                        exit={{ opacity: 0, y: -40, filter: 'blur(20px)' }}
                                        transition={{ duration: 0.9, ease: "circOut" }}
                                        className="max-w-7xl mx-auto space-y-24 pb-64"
                                    >
                                        <IntentCanvas onGenerated={handleNewIvcu} addLog={addLog} />
                                        <AnimatePresence>
                                            {currentIvcu && (
                                                <motion.div
                                                    initial={{ opacity: 0, scale: 0.97, y: 80 }}
                                                    animate={{ opacity: 1, scale: 1, y: 0 }}
                                                    transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
                                                >
                                                    <ReviewPanel ivcu={currentIvcu} />
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </motion.div>
                                )}

                                {activeTab === 'graph' && (
                                    <motion.div
                                        key="graph"
                                        initial={{ opacity: 0, scale: 0.92 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="h-full w-full p-12"
                                    >
                                        <MemoryGraph />
                                    </motion.div>
                                )}

                                {activeTab === 'monitor' && (
                                    <motion.div
                                        key="monitor"
                                        initial={{ opacity: 0, x: 50 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0 }}
                                        className="h-full p-12"
                                    >
                                        <Monitor history={ivcuHistory} />
                                    </motion.div>
                                )}

                                {activeTab === 'tests' && (
                                    <motion.div
                                        key="tests"
                                        initial={{ opacity: 0, scale: 1.1 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="h-full p-12"
                                    >
                                        <TestHub />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Kinetic Telemetry Hub */}
                        <aside className="w-[500px] glass border-l border-white/5 flex flex-col hidden xl:flex z-40 bg-black/70 shadow-4xl relative">
                            <div className="absolute inset-0 bg-gradient-to-b from-sky-500/[0.02] to-transparent pointer-events-none" />
                            <div className="p-14 border-b border-white/10 flex items-center justify-between bg-white/[0.01]">
                                <div className="flex flex-col gap-2">
                                    <div className="flex items-center space-x-6">
                                        <TerminalIcon size={20} className="text-sky-400 bloom" />
                                        <span className="text-[12px] font-bold uppercase tracking-[0.6em] text-slate-300 mono">Axiom Link Telemetry</span>
                                    </div>
                                </div>
                                <motion.div
                                    animate={{ opacity: [0.5, 1, 0.5] }}
                                    transition={{ duration: 2.5, repeat: Infinity }}
                                    className="px-5 py-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-[10px] mono text-emerald-400 font-bold tracking-widest shadow-lg shadow-emerald-500/5"
                                >
                                    LIVE_FEED
                                </motion.div>
                            </div>

                            <div className="flex-1 overflow-hidden flex flex-col">
                                <Terminal logs={logs} />
                            </div>

                            <div className="p-16 bg-black/50 border-t border-white/10 space-y-16">
                                <div className="space-y-12">
                                    <div className="flex justify-between items-center px-2">
                                        <h4 className="text-[11px] font-bold text-slate-600 uppercase tracking-[0.5em] mono">Neural Integrity</h4>
                                        <span className="text-[11px] text-sky-400 font-bold mono bloom">99.1%</span>
                                    </div>
                                    <div className="space-y-10">
                                        <TelemetryItem label="Memory Core" value="0.08 GB" color="text-sky-400" icon={<Activity size={16} />} />
                                        <TelemetryItem label="Truth Engine" value="Optimized" color="text-emerald-400" icon={<CheckCircle2 size={16} />} />
                                        <TelemetryItem label="Semantic Rate" value="2.1 GB/s" color="text-slate-100" icon={<Zap size={16} />} />
                                    </div>
                                </div>

                                <div className="p-12 rounded-[3rem] bg-white/[0.02] border border-white/10 space-y-10 relative overflow-hidden group shadow-inner">
                                    <div className="absolute inset-0 bg-gradient-to-tr from-sky-500/15 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-1000" />
                                    <div className="flex justify-between items-center relative z-10">
                                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.4em] mono">Total System Uptime</span>
                                        <span className="text-[16px] font-mono text-slate-200 font-bold tracking-tighter">1,288.4H</span>
                                    </div>
                                    <div className="w-full bg-black/60 h-3 rounded-full overflow-hidden border border-white/10 relative z-10 p-[2px]">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: '98.2%' }}
                                            transition={{ duration: 3, ease: "circOut" }}
                                            className="bg-sky-500 h-full rounded-full shadow-[0_0_25px_#0ea5e9]"
                                        />
                                    </div>
                                </div>
                            </div>
                        </aside>
                    </div>
                </main>
            </motion.div>
        </div>
    );
};

const NavItem = ({ active, icon, onClick, label }: any) => (
    <button
        onClick={onClick}
        className={`group relative p-7 rounded-[3rem] transition-all duration-1000 ${active
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-[0_0_50px_rgba(14,165,233,0.2)]'
                : 'text-slate-700 hover:text-slate-400 hover:bg-white/5'
            }`}
    >
        {icon}

        <div className="absolute left-full ml-16 px-8 py-5 bg-[#010204] border border-white/10 text-[12px] font-bold text-slate-300 rounded-[2rem] opacity-0 group-hover:opacity-100 transition-all transform scale-95 group-hover:scale-100 group-hover:translate-x-6 whitespace-nowrap z-[100] pointer-events-none shadow-4xl backdrop-blur-3xl border-l-4 border-l-sky-500">
            {label}
        </div>

        {active && (
            <motion.div
                layoutId="sidebar-active-indicator"
                className="absolute -left-3 w-2.5 h-14 bg-sky-500 rounded-full shadow-[0_0_25px_#0ea5e9]"
            />
        )}
    </button>
);

const TelemetryItem = ({ label, value, color, icon }: any) => (
    <div className="flex items-center justify-between text-[12px] group">
        <div className="flex items-center space-x-6 text-slate-500">
            <div className="p-3 rounded-2xl bg-white/5 border border-white/5 group-hover:border-sky-500/40 group-hover:bg-sky-500/5 transition-all duration-500">
                {icon}
            </div>
            <span className="uppercase tracking-[0.4em] mono text-[11px] font-semibold group-hover:text-slate-300 transition-colors">{label}</span>
        </div>
        <span className={`${color} mono font-bold group-hover:scale-110 transition-transform`}>{value}</span>
    </div>
);

export default App;
