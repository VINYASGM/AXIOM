
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2, Circle, ShieldCheck, ArrowUpRight, Code, Download, AlertCircle, Loader2, ChevronRight, Fingerprint, Lock, Zap, FileBadge2
} from 'lucide-react';
import { IVCU, VerificationTier } from '../types';
import Button from './Button';

import {
  GitFork
} from 'lucide-react';

interface Props {
  ivcu: IVCU;
  onExplore?: () => void;
}

const ReviewPanel: React.FC<Props> = ({ ivcu, onExplore }) => {
  const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
  const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 lg:grid-cols-12 gap-6 pb-12">
      <motion.div variants={item} className="lg:col-span-7 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center">
            <Code size={14} className="mr-2 text-emerald-400" />
            Verified Artifact Implementation
          </h3>
          <div className="flex space-x-3">
            <Button variant="secondary" size="sm" icon={GitFork} onClick={onExplore}>Explore Alternatives</Button>
            <Button variant="secondary" size="sm" icon={Download}>Download</Button>
            <Button variant="primary" size="sm" icon={Zap} iconPosition="right">Deploy Artifact</Button>
          </div>
        </div>

        <div className="glass rounded-[2rem] overflow-hidden border border-white/5 shadow-2xl group relative">
          <div className="bg-slate-900/60 px-6 py-4 flex items-center justify-between border-b border-white/5">
            <div className="flex items-center space-x-4">
              <div className="flex space-x-1.5">
                <div className="w-2 h-2 rounded-full bg-red-500/20" />
                <div className="w-2 h-2 rounded-full bg-amber-500/20" />
                <div className="w-2 h-2 rounded-full bg-emerald-500/20" />
              </div>
              <span className="text-[9px] font-mono text-slate-500 flex items-center">
                <Lock size={10} className="mr-1.5 opacity-50" />
                kernel_artifact.tsx
              </span>
            </div>
          </div>
          <div className="p-8 font-mono text-sm leading-relaxed overflow-x-auto bg-[#020617]/40 custom-scroll max-h-[640px]">
            <pre className="text-blue-300/80 whitespace-pre-wrap"><code>{ivcu.code || "// STANDBY: SYMBOLS LOADING..."}</code></pre>
          </div>
        </div>
      </motion.div>

      <div className="lg:col-span-5 space-y-6">
        <motion.div variants={item} className="glass rounded-[2rem] p-8 border-l-4 border-emerald-500 relative overflow-hidden group">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <ShieldCheck size={18} className="text-emerald-400" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Certainty Index</span>
            </div>
          </div>
          <div className="flex items-baseline space-x-3">
            <span className="text-6xl font-bold text-white tracking-tighter">{(ivcu.confidence * 100).toFixed(1)}<span className="text-2xl text-slate-500 ml-1">%</span></span>
            <span className="text-emerald-400 text-[10px] font-bold flex items-center bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 uppercase tracking-widest">Optimal</span>
          </div>
        </motion.div>

        <motion.div variants={item} className="glass rounded-[2rem] p-6 space-y-4 border border-white/5">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
              <Fingerprint size={14} className="text-cyan-400" />
              Verification Pipeline
            </h4>
          </div>
          <div className="space-y-3">
            {ivcu.verificationTiers.map((tier, idx) => (
              <TierItem key={idx} tier={tier} index={idx} />
            ))}
          </div>
        </motion.div>

        <motion.div variants={item} className="bg-gradient-to-br from-emerald-500/10 via-transparent p-8 rounded-[2rem] border border-emerald-500/20 space-y-6">
          <div className="flex items-center space-x-3">
            <FileBadge2 size={20} className="text-emerald-400" />
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-[0.2em]">Signed Certificate</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed font-medium">Compliance proof ready for Zero-Knowledge handover.</p>
          <Button variant="tertiary" size="md" icon={ChevronRight} iconPosition="right" className="w-full">Export Signed Bundle</Button>
        </motion.div>
      </div>
    </motion.div>
  );
};

const TierItem = ({ tier, index }: { tier: VerificationTier; index: number }) => {
  const isPassed = tier.status === 'passed';
  return (
    <div className={`p-3 rounded-xl border transition-all ${isPassed ? 'bg-emerald-500/5 border-emerald-500/10 text-emerald-400' : 'bg-white/[0.02] border-white/5 opacity-50'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {isPassed ? <CheckCircle2 size={12} /> : <Circle size={12} />}
          <span className="text-[10px] font-bold tracking-widest uppercase">{tier.name}</span>
        </div>
        {isPassed && <span className="text-[9px] font-bold uppercase tracking-widest opacity-60">Verified</span>}
      </div>
    </div>
  );
};

export default ReviewPanel;
