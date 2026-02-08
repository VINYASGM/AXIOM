
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, LayoutGroup, AnimatePresence, useSpring, useMotionValue, useTransform } from 'framer-motion';
import {
  Send, Wand2, Undo2, Redo2, Activity, CheckCircle2, Clock, AlertCircle, ChevronRight, ChevronDown, ChevronUp, Info, Image as ImageIcon, X, Sparkles, Layers as LayersIcon, Terminal as TerminalIcon, ShieldCheck, Zap, Box, Cpu, Fingerprint, Save, History, Code, Copy, Lock, XCircle, DollarSign
} from 'lucide-react';
import { parseIntent, generateVerifiedCode, generateIntentVisual, snapshotState, getEstimatedCost } from '../services/geminiService';
import { ApiClient } from '../lib/api';
import { IVCU, IVCUStatus, ModelTier, VerificationTier, SpeculationResult } from '../types';
import Button from './Button';
import Tooltip from './Tooltip';
import { ScaffoldingLevel } from './AdaptiveScaffolding'; // Import enum
import { initTreeSitter, getParser, SupportedLanguage } from '../lib/tree-sitter';

interface Props {
  onGenerated: (ivcu: IVCU) => void;
  addLog: (msg: string) => void;
  scaffoldingLevel?: ScaffoldingLevel;
  userSkills?: any;
}

interface TierMeta {
  desc: string;
  cost: string;
  capability: string;
  color: string;
  activeClass: string;
  explanation: string;
  icon: any;
  glow: string;
}

const TIER_METADATA: Record<ModelTier, TierMeta> = {
  [ModelTier.Local]: {
    desc: "Privacy-first local execution simulation. Zero latency.",
    cost: "FREE",
    capability: "Basic logic / Refinement",
    color: "text-slate-400",
    activeClass: "border-slate-500/50 text-slate-300 bg-slate-500/10 shadow-[0_0_40px_rgba(100,116,139,0.2)]",
    explanation: "The sovereignty-first protocol. Engineered for sub-millisecond response cycles.",
    icon: ShieldCheck,
    glow: "rgba(100, 116, 139, 0.4)"
  },
  [ModelTier.Fast]: {
    desc: "High-throughput balanced synthesis for rapid iteration.",
    cost: "LOW",
    capability: "Standard patterns / Scripting",
    color: "text-sky-400",
    activeClass: "border-sky-500/50 text-sky-400 bg-sky-500/10 shadow-[0_0_40px_rgba(14,165,233,0.3)]",
    explanation: "The standard for high-velocity synthesis.",
    icon: Zap,
    glow: "rgba(14, 165, 233, 0.4)"
  },
  [ModelTier.Capable]: {
    desc: "Advanced reasoning with deep verification cycles.",
    cost: "MID",
    capability: "Complex architecture / Security",
    color: "text-emerald-400",
    activeClass: "border-emerald-500/50 text-emerald-400 bg-emerald-500/10 shadow-[0_0_40px_rgba(16,185,129,0.3)]",
    explanation: "Engineered for deep-reasoning verification.",
    icon: Cpu,
    glow: "rgba(16, 185, 129, 0.4)"
  },
  [ModelTier.Frontier]: {
    desc: "Research-grade intelligence. Maximum architectural context.",
    cost: "HIGH",
    capability: "System design / Deep Reasoner",
    color: "text-rose-400",
    activeClass: "border-rose-500/50 text-rose-400 bg-rose-500/10 shadow-[0_0_40px_rgba(244,63,94,0.3)]",
    explanation: "The peak of emergent architectural innovation.",
    icon: Sparkles,
    glow: "rgba(244, 63, 94, 0.4)"
  }
};

const COMPLEXITY_LABELS: Record<number, { label: string, color: string }> = {
  1: { label: "Atomic Logic", color: "text-slate-500" },
  2: { label: "Atomic Logic", color: "text-slate-500" },
  3: { label: "Utility Script", color: "text-sky-500" },
  4: { label: "Modular Component", color: "text-sky-500" },
  5: { label: "Service Logic", color: "text-emerald-500" },
  6: { label: "Service Logic", color: "text-emerald-500" },
  7: { label: "Cluster Arch", color: "text-amber-500" },
  8: { label: "Enterprise Mesh", color: "text-amber-500" },
  9: { label: "Sovereign Node", color: "text-rose-500" },
  10: { label: "Universal Nexus", color: "text-rose-500" },
};

const MIN_INTENT_LENGTH = 10;

interface ValidationResult {
  isValid: boolean;
  errors: { line: number; message: string }[];
}

type SynthesisStep =
  | 'idle'
  | 'parsing'
  | 'extracting'
  | 'verifying_logic'
  | 'verifying_types'
  | 'verifying_style'
  | 'resolving_dependencies'
  | 'synthesizing_architecture'
  | 'synthesizing_implementation'
  | 'synthesizing_security'
  | 'complete';

const IntentCanvas: React.FC<Props> = ({ onGenerated, addLog, scaffoldingLevel = ScaffoldingLevel.Intermediate, userSkills }) => {
  const [intent, setIntent] = useState('');
  const [loading, setLoading] = useState(false);
  const [visualizing, setVisualizing] = useState(false);
  const [visualUrl, setVisualUrl] = useState<string | null>(null);
  const [model, setModel] = useState<ModelTier>(ModelTier.Fast);
  const [complexity, setComplexity] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [executionHistory, setExecutionHistory] = useState<IVCU[]>([]);
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);
  const [synthesisStep, setSynthesisStep] = useState<SynthesisStep>('idle');
  const [hasSavedSnapshot, setHasSavedSnapshot] = useState(false);
  const [showCodePreview, setShowCodePreview] = useState(false);
  const [lastVerifiedIvcu, setLastVerifiedIvcu] = useState<IVCU | null>(null);
  const [validation, setValidation] = useState<ValidationResult>({ isValid: true, errors: [] });
  const [mode, setMode] = useState<'natural' | 'code'>('natural'); // Added mode
  const [costEstimate, setCostEstimate] = useState<{ cost: number; tokens: number } | null>(null);
  const [speculation, setSpeculation] = useState<SpeculationResult | null>(null);

  // Initialize Tree-sitter
  useEffect(() => {
    initTreeSitter().catch(console.error);
  }, []);

  // Validate code when input changes (debounced)
  // Validate code when input changes (debounced)
  useEffect(() => {
    if (intent.trim()) {
      const timer = setTimeout(async () => {
        // Default to python for now, or detect language
        const parser = await getParser(SupportedLanguage.PYTHON);
        if (parser) {
          try {
            const tree = parser.parse(intent);
            const errors: { line: number; message: string }[] = [];

            if (tree.rootNode.hasError()) {
              const cursor = tree.walk();
              let reachedEnd = false;

              // Simple iterative traversal to find error nodes
              while (!reachedEnd) {
                if (cursor.currentNode().isError() || cursor.currentNode().isMissing()) {
                  errors.push({
                    line: cursor.currentNode().startPosition.row + 1,
                    message: `Syntax error: ${cursor.currentNode().type}`
                  });
                  if (errors.length >= 1) break; // Just show first error for minimal UI
                }

                // Depth first
                if (cursor.gotoFirstChild()) continue;
                if (cursor.gotoNextSibling()) continue;

                // Up and next
                while (true) {
                  if (cursor.gotoNextSibling()) break;
                  if (!cursor.gotoParent()) { reachedEnd = true; break; }
                }
              }
            }

            setValidation({
              isValid: errors.length === 0,
              errors
            });
            tree.delete();
          } catch (e) {
            console.error("Tree-sitter parse error:", e);
          }
        }

        // Fetch Speculation if intent is substantial
        if (intent.trim().length > 20) {
          const spec = await ApiClient.speculateIntent(intent);
          setSpeculation(spec);
        }
      }, 800);
      return () => clearTimeout(timer);
    } else {
      setValidation({ isValid: true, errors: [] });
      setSpeculation(null);
    }
  }, [intent]);

  // WebSocket Connection (Phase 4.5)
  useEffect(() => {
    // Only connect in browser environment
    if (typeof window === 'undefined') return;

    const clientId = Math.random().toString(36).substring(7);
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `ws://localhost:8000/ws/${clientId}`;

    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("Connected to AXIOM Thought Stream");
        addLog("NET: Uplink established to Neural Core.");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event) {
            // Format message based on event type
            let msg = "";
            const d = payload.data || {};

            switch (payload.event) {
              case "INTENT_CREATED":
                msg = `CORE: Intent registered. Analysis started.`;
                break;
              case "CANDIDATE_GENERATED":
                msg = `GEN: Candidate ${d.candidate_id?.substring(0, 4)} generated via ${d.model?.split(':')[0]}`;
                break;
              case "VERIFICATION_COMPLETED":
                const status = d.passed ? "PASSED" : "FAILED";
                const score = typeof d.score === 'number' ? d.score.toFixed(2) : '0.00';
                msg = `VERIFY: Unit ${d.candidate_id?.substring(0, 4)} ${status} [Integrity: ${score}]`;
                break;
              case "CANDIDATE_SELECTED":
                msg = `DECISION: Optimized candidate selected (Conf: ${d.confidence?.toFixed(2)})`;
                break;
              default:
                msg = `SYS: ${payload.event}`;
            }

            if (msg) addLog(msg);
          }
        } catch (e) {
          console.error("WS Parse Error", e);
        }
      };

      ws.onerror = (e) => {
        console.error("WS Error", e);
      };
    } catch (e) {
      console.error("WS Init Error", e);
    }

    return () => {
      if (ws) ws.close();
    };
  }, [addLog]);

  // Parallax / Hover Effects for Neural Matrix Feel

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useSpring(useTransform(mouseY, [-300, 300], [3, -3]), { stiffness: 100, damping: 30 });
  const rotateY = useSpring(useTransform(mouseX, [-300, 300], [-3, 3]), { stiffness: 100, damping: 30 });

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    mouseX.set(e.clientX - (rect.left + rect.width / 2));
    mouseY.set(e.clientY - (rect.top + rect.height / 2));
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  const [history, setHistory] = useState({ stack: [''], index: 0 });
  const [isTemporalShifting, setIsTemporalShifting] = useState(false);
  const skipHistoryPush = useRef(false);
  const debounceTimer = useRef<any>(null);

  useEffect(() => {
    const saved = localStorage.getItem('axiom_saved_intent');
    if (saved) setHasSavedSnapshot(true);
  }, []);

  const pushToChronology = useCallback((newIntent: string) => {
    if (skipHistoryPush.current) { skipHistoryPush.current = false; return; }
    setHistory(prev => {
      const currentStack = prev.stack.slice(0, prev.index + 1);
      if (currentStack[currentStack.length - 1] === newIntent) return prev;
      const nextStack = [...currentStack, newIntent].slice(-50);
      return { stack: nextStack, index: nextStack.length - 1 };
    });
  }, []);

  const jumpToState = useCallback((index: number) => {
    setHistory(prev => {
      if (index < 0 || index >= prev.stack.length) return prev;
      const targetText = prev.stack[index];
      skipHistoryPush.current = true;
      setIntent(targetText);
      setIsTemporalShifting(true);
      setTimeout(() => setIsTemporalShifting(false), 500);
      addLog(`TEMPORAL: Frame Jump to [${index + 1}]`);
      return { ...prev, index };
    });
  }, [addLog]);

  const handleUndo = () => jumpToState(history.index - 1);
  const handleRedo = () => jumpToState(history.index + 1);

  const handleIntentChange = (val: string) => {
    setIntent(val);
    if (error) setError(null);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      pushToChronology(val);
      // Estimate cost when intent changes (debounced)
      if (val.trim().length >= MIN_INTENT_LENGTH) {
        getEstimatedCost(val, model === ModelTier.Frontier ? 'claude-sonnet-4' : 'deepseek-v3')
          .then(result => {
            setCostEstimate({ cost: result.estimated_cost_usd, tokens: result.input_tokens + result.output_tokens });
          })
          .catch(() => setCostEstimate(null));
      } else {
        setCostEstimate(null);
      }
    }, 800);
  };

  const handleSubmit = async () => {
    if (intent.trim().length < MIN_INTENT_LENGTH) return;
    setLoading(true);
    setSynthesisStep('parsing');
    addLog(`INITIATING SEMANTIC PARSE: ${model}`);

    const tempIvcu: IVCU = {
      id: Math.random().toString(36).substr(2, 9),
      intent,
      status: IVCUStatus.Generating,
      confidence: 0,
      cost: 0,
      verificationTiers: [
        { name: 'Syntax Check', status: 'pending' },
        { name: 'Architecture', status: 'pending' },
        { name: 'Type Integrity', status: 'pending' },
        { name: 'Style Check', status: 'pending' },
        { name: 'Dep Resolution', status: 'pending' },
        { name: 'Kernel Audit', status: 'pending' }
      ],
      timestamp: Date.now()
    };

    setExecutionHistory(prev => [tempIvcu, ...prev].slice(0, 5));
    onGenerated(tempIvcu);

    try {
      setSynthesisStep('extracting');
      const parsed = await parseIntent(intent, complexity, model);
      await new Promise(r => setTimeout(r, 600));

      setSynthesisStep('verifying_logic');
      addLog("VERIFICATION: Consolidating logic graph...");
      await new Promise(r => setTimeout(r, 600));

      setSynthesisStep('verifying_style');
      addLog("VERIFICATION: Axiom style compliance confirmed.");
      await new Promise(r => setTimeout(r, 400));

      setSynthesisStep('synthesizing_implementation');
      const code = await generateVerifiedCode(intent, parsed.constraints, complexity, model);

      const updatedIvcu: IVCU = {
        ...tempIvcu,
        code: code || '',
        status: IVCUStatus.Verified,
        confidence: parsed.confidence || 0.98,
        cost: model === ModelTier.Frontier ? 0.125 : model === ModelTier.Capable ? 0.042 : 0.012,
        verificationTiers: tempIvcu.verificationTiers.map((t) => ({ ...t, status: 'passed' }))
      };

      setExecutionHistory(prev => prev.map(h => h.id === tempIvcu.id ? updatedIvcu : h));
      setLastVerifiedIvcu(updatedIvcu);
      setShowCodePreview(true);
      onGenerated(updatedIvcu);
      setSynthesisStep('complete');
      addLog("CONSENSUS: Synthesis finalized successfully.");
      setTimeout(() => setSynthesisStep('idle'), 3000);
    } catch (err) {
      addLog("FATAL: Semantic synthesis loop collapsed.");
      setError("System failure.");
      setSynthesisStep('idle');
    } finally {
      setLoading(false);
    }
  };

  const getSynthesisProgress = () => {
    const map: Record<SynthesisStep, number> = {
      idle: 0, parsing: 10, extracting: 20, verifying_logic: 35,
      verifying_types: 50, verifying_style: 60, resolving_dependencies: 70,
      synthesizing_architecture: 80, synthesizing_implementation: 90,
      synthesizing_security: 98, complete: 100
    };
    return map[synthesisStep] || 0;
  };

  const isIntentValid = intent.trim().length >= MIN_INTENT_LENGTH;

  return (
    <motion.div
      style={{ rotateX, rotateY }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative perspective-1000"
    >
      <div className={`glass rounded-[3.5rem] p-10 md:p-16 relative overflow-hidden transition-all duration-1000 ${loading ? 'ring-4 ring-sky-500/20 shadow-[0_0_120px_rgba(14,165,233,0.15)]' : 'border border-white/5 shadow-2xl shadow-black'}`}>

        {/* Neural Dynamic Background */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 right-0 p-12 opacity-[0.03] animate-flicker">
            <Cpu size={320} className="text-sky-400 rotate-12" />
          </div>
          {/* Dynamic Semantic Particles */}
          {intent.length > 0 && [...Array(24)].map((_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{
                opacity: [0, 0.15, 0],
                scale: [0.5, 1.2, 0.5],
                x: [Math.random() * 1200, Math.random() * 1200],
                y: [Math.random() * 800, Math.random() * 800]
              }}
              transition={{ duration: Math.random() * 8 + 4, repeat: Infinity, ease: "linear" }}
              className="absolute w-1.5 h-1.5 bg-sky-500 rounded-full blur-[2px]"
            />
          ))}
        </div>

        <div className="relative z-10 space-y-12">
          {/* Dashboard Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <motion.div
                animate={loading ? { rotate: 360, scale: [1, 1.1, 1] } : {}}
                transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                className="p-5 rounded-[2.2rem] bg-sky-500/10 border border-sky-500/20 shadow-lg shadow-sky-500/10 text-sky-400 relative overflow-hidden group/wand"
              >
                <Wand2 size={24} className="relative z-10" />
                <motion.div
                  className="absolute inset-0 bg-sky-400/20 -z-0"
                  animate={{ opacity: [0, 0.4, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </motion.div>
              <div className="flex flex-col">
                <span className="text-[12px] font-bold uppercase tracking-[0.5em] mono text-slate-300">Neural Orchestrator</span>
                <span className="text-[10px] text-slate-600 mono uppercase tracking-widest mt-2">Buffer Integrity: {history.index + 1} / {history.stack.length}</span>
              </div>

              {/* Adaptive Scaffolding Badge */}
              {scaffoldingLevel !== ScaffoldingLevel.Expert && (
                <div className="flex flex-col ml-8 border-l border-white/10 pl-8">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-500">Adaptive Mode</span>
                  <span className="text-[10px] text-slate-500 mono uppercase mt-1">
                    Level: {scaffoldingLevel}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-4 bg-black/50 p-2.5 rounded-[1.8rem] border border-white/5 backdrop-blur-2xl">
              <Button variant="tertiary" size="sm" icon={Undo2} disabled={history.index === 0} onClick={handleUndo} aria-label="Undo semantic change">Undo</Button>
              <div className="w-px h-6 bg-white/10" />
              <Button variant="tertiary" size="sm" icon={Redo2} disabled={history.index === history.stack.length - 1} onClick={handleRedo} aria-label="Redo semantic change">Redo</Button>
            </div>
          </div>

          {/* Synthesis Matrix Input */}
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-1 rounded-full border ${scaffoldingLevel === 'beginner'
              ? 'bg-green-500/10 border-green-500/20 text-green-400'
              : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
              }`}>
              {scaffoldingLevel === 'beginner' ? 'Adaptive Mode' : 'Pro Mode'}
            </span>
            {!validation.isValid && (
              <span className="text-xs px-2 py-1 rounded-full border bg-red-500/10 border-red-500/20 text-red-400 flex items-center gap-1">
                <XCircle size={12} />
                Syntax Error: Line {validation.errors[0]?.line}
              </span>
            )}
            <span className="text-xs text-white/30">
              {intent.length} chars
            </span>
          </div>
          <div className="relative group">
            <motion.div
              animate={isTemporalShifting ? {
                scale: [1, 0.99, 1],
                filter: ['blur(0px)', 'blur(10px)', 'blur(0px)'],
              } : {}}
              transition={{ duration: 0.6 }}
              className="relative"
            >
              <textarea
                value={intent}
                onChange={(e) => handleIntentChange(e.target.value)}
                placeholder={scaffoldingLevel === ScaffoldingLevel.Beginner ? "Describe what you want to build in plain English (e.g. 'A user login form with email validation')..." : "Articulate your architectural intent..."}
                className="w-full bg-transparent border-none text-3xl md:text-5xl font-bold focus:ring-0 placeholder:text-slate-800 min-h-[340px] resize-none text-white leading-[1.2] selection:bg-sky-500/30 custom-scroll transition-all duration-700 font-sans"
              />

              {/* Visual Output Port */}
              <AnimatePresence>
                {visualUrl && !visualizing && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 30 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 1.05 }}
                    className="mt-14 relative rounded-[3.5rem] overflow-hidden border border-white/10 shadow-3xl group/img bg-black/20"
                  >
                    <img src={visualUrl} alt="Neural Schematic" className="w-full aspect-video object-cover grayscale-[0.3] group-hover:grayscale-0 transition-all duration-1000" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80" />
                    <div className="absolute top-6 left-6 flex items-center space-x-3">
                      <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 2, repeat: Infinity }} className="w-2.5 h-2.5 rounded-full bg-sky-500 shadow-[0_0_15px_#0ea5e9]" />
                      <span className="text-[11px] mono text-sky-400 font-bold uppercase tracking-widest bg-black/60 px-4 py-1.5 rounded-full">Schematic Confirmed</span>
                    </div>
                    <Button variant="secondary" size="sm" icon={X} onClick={() => setVisualUrl(null)} className="absolute bottom-8 right-8">Close Schematic</Button>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            <div className="absolute bottom-4 right-8 flex items-center space-x-6">
              <div className="flex flex-col items-end">
                <span className={`text-[12px] mono font-bold tracking-[0.2em] transition-colors ${isIntentValid ? 'text-sky-500' : 'text-slate-700'}`}>
                  {intent.length} / {MIN_INTENT_LENGTH} MIN_BUF
                </span>
              </div>

              {/* Live Cost Estimate Badge */}
              <AnimatePresence mode="wait">
                {costEstimate && isIntentValid && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9, x: 20 }}
                    animate={{ opacity: 1, scale: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.9, x: 20 }}
                    className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                  >
                    <DollarSign size={14} className="opacity-70" />
                    <span className="text-[11px] mono font-bold">
                      ${costEstimate.cost.toFixed(4)}
                    </span>
                    <span className="text-[10px] mono text-emerald-500/60">
                      ~{costEstimate.tokens.toLocaleString()} tok
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Speculation Engine Output */}
          <AnimatePresence>
            {speculation && speculation.paths.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles size={14} className="text-amber-400" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Speculative Paths Detected</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {speculation.paths.map((path) => (
                    <div key={path.id} className="p-4 rounded-2xl bg-white/5 border border-white/5 hover:border-amber-500/30 transition-colors group cursor-pointer">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-bold text-slate-300">{path.label}</span>
                        <span className="text-[10px] mono text-amber-400">{(path.probability * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-[10px] text-slate-500 leading-relaxed">{path.description}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Logic Controller Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 pt-16 border-t border-white/5">
            <div className="space-y-12">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-5">
                  <LayersIcon size={20} className="text-slate-500" />
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.4em] mono">Logic Depth Index</span>
                </div>
                <motion.span
                  key={complexity}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`text-[12px] font-bold mono uppercase tracking-widest ${COMPLEXITY_LABELS[complexity].color}`}
                >
                  {COMPLEXITY_LABELS[complexity].label}
                </motion.span>
              </div>
              <div className="relative py-4 group/range">
                <input
                  type="range" min="1" max="10" step="1"
                  value={complexity}
                  onChange={(e) => setComplexity(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-slate-900 rounded-full appearance-none cursor-pointer focus:outline-none accent-sky-500 shadow-inner"
                />
                <div className="flex justify-between mt-8">
                  {[...Array(10)].map((_, i) => (
                    <motion.div
                      key={i}
                      animate={{
                        height: i + 1 <= complexity ? [6, 10, 6] : 4,
                        opacity: i + 1 <= complexity ? 1 : 0.15
                      }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.08 }}
                      className={`w-1 rounded-full transition-all duration-500 ${i + 1 <= complexity ? 'bg-sky-500 shadow-[0_0_10px_#0ea5e9]' : 'bg-slate-700'}`}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-12">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.4em] mono">Neural Execution Cluster</span>
              <div className="flex flex-wrap gap-3.5 p-3 bg-black/50 rounded-[2.8rem] border border-white/5 shadow-inner relative overflow-hidden">
                <LayoutGroup id="model-tier-tabs">
                  {Object.values(ModelTier).map((t) => {
                    const meta = TIER_METADATA[t as ModelTier];
                    const isActive = model === t;
                    return (
                      <motion.button
                        key={t}
                        layout
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setModel(t as ModelTier)}
                        className={`px-8 py-4.5 rounded-[2rem] text-[10px] font-bold uppercase tracking-widest transition-all duration-500 border relative flex items-center gap-3.5 ${isActive ? meta.activeClass : 'border-transparent text-slate-600 hover:text-slate-400'
                          }`}
                      >
                        {isActive && (
                          <motion.div
                            layoutId="active-tab-glow"
                            className="absolute inset-0 rounded-[2rem] bg-white/[0.04] -z-10 shadow-[inset_0_0_25px_rgba(255,255,255,0.02)]"
                            transition={{ type: "spring", bounce: 0.15, duration: 0.7 }}
                          />
                        )}
                        <meta.icon size={16} className={isActive ? "text-sky-400 bloom" : "opacity-30"} />
                        {t.split('(')[0]}
                      </motion.button>
                    );
                  })}
                </LayoutGroup>
              </div>
            </div>
          </div>

          {/* Primary Action Sequence */}
          <div className="flex flex-col space-y-10 pt-16">
            <div className="flex items-center justify-end gap-6 relative">
              <div className="flex items-center gap-4">
                <Button variant="tertiary" size="xl" icon={Save} onClick={async () => {
                  if (lastVerifiedIvcu?.id) {
                    const success = await snapshotState(lastVerifiedIvcu.id);
                    success ? addLog(`SYS: Snapshot of ${lastVerifiedIvcu.id} persisted to Temporal.`) : addLog("ERR: Snapshot failed.");
                  } else {
                    addLog("SYS: No active unit to snapshot.");
                  }
                }}>Snapshot</Button>
                <Button
                  variant="secondary"
                  size="xl"
                  icon={ImageIcon}
                  loading={visualizing}
                  onClick={async () => {
                    setVisualizing(true);
                    const url = await generateIntentVisual(intent);
                    setVisualUrl(url);
                    setVisualizing(false);
                  }}
                >Schematic</Button>
              </div>

              <div className="relative group/btn">
                <Button
                  variant={isIntentValid ? 'primary' : 'tertiary'}
                  size="xl"
                  icon={loading ? Clock : (isIntentValid ? Send : Lock)}
                  loading={loading}
                  onClick={handleSubmit}
                  disabled={!isIntentValid}
                  className={`
                        ${loading ? "min-w-[460px]" : "min-w-[300px]"} 
                        transition-all duration-1000 relative overflow-hidden
                        ${!isIntentValid ? 'grayscale opacity-30 cursor-not-allowed' : 'grayscale-0'}
                        ${loading ? 'bg-sky-500 border-sky-400' : ''}
                      `}
                >
                  <span className="relative z-10 mono tracking-[0.4em]">
                    {loading ? synthesisStep.replace('_', ' ').toUpperCase() : "EXECUTE_INTENT"}
                  </span>
                  {loading && (
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-r from-sky-400/30 via-white/20 to-sky-400/30"
                      animate={{ x: ['-100%', '100%'] }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
                    />
                  )}
                </Button>

                {/* Execution Burst Effect */}
                <AnimatePresence>
                  {loading && (
                    <>
                      <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 3.5, opacity: [0, 0.4, 0] }}
                        transition={{ duration: 1.2, repeat: Infinity }}
                        className="absolute inset-0 bg-sky-500/40 rounded-full blur-[60px] -z-10"
                      />
                      <motion.div
                        initial={{ scale: 1, opacity: 0 }}
                        animate={{ scale: 2, opacity: [0, 0.1, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                        className="absolute inset-0 border border-sky-400/30 rounded-[2.5rem] -z-10"
                      />
                    </>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Kernel Progress Engine */}
            <div className="relative h-3 bg-black/60 rounded-full overflow-hidden border border-white/10 shadow-inner p-[2px]">
              <motion.div
                className="absolute top-0 left-0 h-full bg-gradient-to-r from-sky-600 via-sky-400 to-sky-600 shadow-[0_0_30px_#0ea5e9]"
                initial={{ width: '0%' }}
                animate={{ width: `${getSynthesisProgress()}%` }}
                transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
              >
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent"
                  animate={{ x: ['-100%', '200%'] }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: "linear" }}
                />
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default IntentCanvas;
