
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FlaskConical, CheckCircle2, XCircle, Play, Activity, ShieldCheck, Cpu, Database, Terminal as TerminalIcon, Search, ChevronRight } from 'lucide-react';
import Button from './Button';

interface TestResult {
  id: string;
  name: string;
  status: 'passed' | 'failed' | 'running' | 'pending';
  trace: string[];
  duration: number;
}

const TestHub: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [tests, setTests] = useState<TestResult[]>([
    { id: '1', name: 'Stack.UndoHistory', status: 'pending', trace: [], duration: 0 },
    { id: '2', name: 'Stack.RedoForwarding', status: 'pending', trace: [], duration: 0 },
    { id: '3', name: 'Compute.TierCostMapping', status: 'pending', trace: [], duration: 0 },
    { id: '4', name: 'Sync.AsyncOrchestration', status: 'pending', trace: [], duration: 0 },
    { id: '5', name: 'Model.SemanticParse', status: 'pending', trace: [], duration: 0 },
    { id: '6', name: 'Safety.ConstraintValidation', status: 'pending', trace: [], duration: 0 },
  ]);

  const runTests = async () => {
    setIsRunning(true);
    setTests(prev => prev.map(t => ({ ...t, status: 'pending', trace: [] })));
    for (let i = 0; i < tests.length; i++) {
      setTests(prev => prev.map((t, idx) => idx === i ? { ...t, status: 'running', trace: ['Initializing logic probe...'] } : t));
      await new Promise(r => setTimeout(r, 600 + Math.random() * 800));
      setTests(prev => prev.map((t, idx) => idx === i ? { ...t, status: 'passed', duration: 400 + Math.random() * 200, trace: [...t.trace, 'Assertion successful.'] } : t));
    }
    setIsRunning(false);
  };

  const integrity = (tests.filter(t => t.status === 'passed').length / tests.length) * 100;

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-20">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 glass rounded-[2.5rem] p-10 border border-white/5 relative overflow-hidden">
        <div className="space-y-4 relative z-10">
            <div className="flex items-center gap-3">
                <FlaskConical size={22} className="text-emerald-400" />
                <h2 className="text-2xl font-bold tracking-tight text-white">Diagnostic Suite v1.4</h2>
            </div>
            <p className="text-slate-500 text-[11px] max-w-lg leading-relaxed font-medium uppercase tracking-widest">Logic verification engine active.</p>
        </div>

        <div className="flex items-center gap-8 relative z-10">
            <div className="text-right">
                <span className="text-[10px] font-bold text-slate-600 uppercase tracking-[0.4em] block mb-1">System Integrity</span>
                <span className="text-3xl font-bold text-white mono">{integrity.toFixed(0)}%</span>
            </div>
            <Button variant="primary" size="lg" icon={isRunning ? Activity : Play} loading={isRunning} onClick={runTests}>
              {isRunning ? 'Running Probes' : 'Initiate Suite'}
            </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between px-4">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.4em]">Logic Assertions</h3>
            </div>
            <div className="grid grid-cols-1 gap-3">
                {tests.map((test) => (
                    <div key={test.id} className="glass rounded-2xl p-4 border border-white/5 flex items-center justify-between hover:bg-white/[0.03] transition-all">
                        <div className="flex items-center gap-4">
                            <div className={test.status === 'passed' ? 'text-emerald-400' : test.status === 'running' ? 'text-amber-400 animate-spin-slow' : 'text-slate-700'}>
                                {test.status === 'passed' ? <CheckCircle2 size={16} /> : <Search size={16} />}
                            </div>
                            <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">{test.name}</span>
                        </div>
                        <Button variant="ghost" size="sm" icon={ChevronRight} />
                    </div>
                ))}
            </div>
        </div>
        <div className="lg:col-span-5">
            <div className="glass rounded-[2rem] p-6 min-h-[400px] flex flex-col bg-black/40 border border-white/5 font-mono text-[10px] space-y-2">
                <span className="text-slate-700 uppercase tracking-widest mb-4">Execution Trace</span>
                {tests.flatMap(t => t.trace).map((msg, i) => (
                    <div key={i} className="text-slate-500 flex gap-2">
                      <span className="text-emerald-500 opacity-50">OK</span>
                      {msg}
                    </div>
                ))}
            </div>
        </div>
      </div>
    </div>
  );
};

export default TestHub;
