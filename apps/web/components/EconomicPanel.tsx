import React from 'react';
import { motion } from 'framer-motion';
import { DollarSign, BarChart3, Info } from 'lucide-react';

const EconomicPanel: React.FC = () => {
  return (
    <div className="flex items-center space-x-8">
      <motion.div 
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        className="hidden sm:flex flex-col items-end"
      >
        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.3em] mb-1">Compute session overhead</span>
        <div className="flex items-center space-x-2 group">
          <div className="p-1.5 rounded-lg bg-emerald-500/5 border border-emerald-500/10 text-emerald-400/80 group-hover:text-emerald-400 group-hover:border-emerald-500/30 transition-all">
            <DollarSign size={12} />
          </div>
          <motion.span 
            className="text-lg font-bold text-white mono tracking-tighter bloom"
            animate={{ opacity: [0.8, 1, 0.8] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            0.428
          </motion.span>
          <span className="text-[10px] text-slate-600 font-bold mono">CREDITS</span>
        </div>
      </motion.div>

      <div className="h-10 w-px bg-white/5" />

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex items-center space-x-4 bg-white/[0.02] border border-white/5 rounded-[1.2rem] px-5 py-2.5 group hover:bg-white/[0.04] transition-all cursor-default shadow-lg shadow-black/20"
      >
        <div className="flex flex-col">
            <div className="flex items-center justify-between min-w-[140px] mb-2">
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                  Budget Velocity <Info size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                </span>
                <span className="text-[10px] text-emerald-400 font-bold mono">12%</span>
            </div>
            <div className="w-full bg-slate-900 h-1.5 rounded-full relative overflow-hidden border border-white/5 shadow-inner">
                <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: '12%' }}
                    transition={{ duration: 1.5, ease: "circOut" }}
                    className="bg-emerald-500 h-full rounded-full relative shadow-[0_0_15px_rgba(16,185,129,0.5)]"
                >
                    {/* Shimmer Effect */}
                    <motion.div 
                      className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                      animate={{ x: ['-100%', '200%'] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />
                </motion.div>
            </div>
        </div>
        <div className="p-2 rounded-xl bg-slate-950/50 text-slate-500 group-hover:text-emerald-400 transition-colors">
          <BarChart3 size={16} />
        </div>
      </motion.div>
    </div>
  );
};

export default EconomicPanel;