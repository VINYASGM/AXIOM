
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Clock, Search, Filter, History, Activity, Cpu, ArrowUpRight, Zap } from 'lucide-react';
import { IVCU, IVCUStatus } from '../types';
import Button from './Button';

interface Props {
  history: IVCU[];
}

const Monitor: React.FC<Props> = ({ history }) => {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard icon={<Activity size={20} className="text-emerald-400" />} label="Success Rate" value="98.2%" trend="+0.4%" />
        <MetricCard icon={<Cpu size={20} className="text-cyan-400" />} label="Avg Latency" value="4.2s" trend="-120ms" />
        <MetricCard icon={<Zap size={20} className="text-violet-400" />} label="Units" value={history.length.toString()} trend="LIVE" />
        <MetricCard icon={<History size={20} className="text-amber-400" />} label="Cache Hit" value="42%" trend="+2.1%" />
      </div>

      <div className="glass rounded-[2.5rem] overflow-hidden border border-white/5 shadow-2xl">
        <div className="p-8 border-b border-white/5 flex flex-col sm:flex-row items-center justify-between bg-white/[0.02] gap-4">
          <h3 className="text-sm font-bold uppercase tracking-[0.4em] text-white flex items-center">
            <History size={18} className="mr-3 text-emerald-500" /> Execution Stream
          </h3>
          <div className="flex items-center gap-3">
            <div className="relative">
                <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600" />
                <input placeholder="Filter..." className="bg-black/40 border border-white/5 rounded-xl pl-10 pr-4 py-2.5 text-[11px] text-slate-300 focus:outline-none w-64" />
            </div>
            <Button variant="secondary" size="md" icon={Filter} />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-900/30 text-[9px] font-bold text-slate-600 uppercase tracking-widest border-b border-white/5">
              <tr>
                <th className="px-8 py-5">Status</th>
                <th className="px-8 py-5">Intent Artifact</th>
                <th className="px-8 py-5">Integrity</th>
                <th className="px-8 py-5">Cost</th>
                <th className="px-8 py-5 text-right">Probes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-[11px] mono">
              {history.map((ivcu) => (
                <tr key={ivcu.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-8 py-5">
                    <span className={`px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-widest border ${ivcu.status === IVCUStatus.Verified ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
                      {ivcu.status}
                    </span>
                  </td>
                  <td className="px-8 py-5 text-slate-300">{ivcu.intent.substring(0, 40)}...</td>
                  <td className="px-8 py-5 text-slate-400">{(ivcu.confidence * 100).toFixed(0)}%</td>
                  <td className="px-8 py-5 text-emerald-500/60">${ivcu.cost.toFixed(3)}</td>
                  <td className="px-8 py-5 text-right">
                    <Button variant="ghost" size="sm">Replay Trace</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
};

const MetricCard = ({ icon, label, value, trend }: any) => (
  <div className="glass rounded-3xl p-6 border border-white/5 flex flex-col space-y-3 group hover:bg-white/[0.02] transition-all">
    <div className="flex items-center justify-between">
      <div className="p-2 rounded-xl bg-white/[0.03] border border-white/5">{icon}</div>
      <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-lg border border-emerald-500/20">{trend}</span>
    </div>
    <div className="flex flex-col">
      <span className="text-[9px] font-bold text-slate-600 uppercase tracking-[0.3em]">{label}</span>
      <span className="text-2xl font-bold text-white tracking-tighter group-hover:text-emerald-400 transition-colors">{value}</span>
    </div>
  </div>
);

export default Monitor;
