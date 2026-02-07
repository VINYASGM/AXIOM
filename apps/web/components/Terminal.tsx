import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  logs: string[];
}

const Terminal: React.FC<Props> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="relative flex-1 flex flex-col overflow-hidden bg-black/40">
      {/* CRT Scanline Effect Local to Terminal */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-[0.03] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_2px,3px_100%]" />
      
      <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 font-mono text-[10px] space-y-1.5 custom-scroll relative z-0"
      >
        <AnimatePresence initial={false}>
          {logs.map((log, i) => {
              const isError = log.includes('ERROR') || log.includes('FATAL') || log.includes('Failure');
              const isSystem = log.includes('[SYSTEM]') || log.includes('INITIATING');
              const isAi = log.includes('[AI]') || log.includes('INTERPRETED') || log.includes('ORCHESTRA');
              
              return (
                <motion.div 
                  key={`${i}-${log.substring(0, 10)}`}
                  initial={{ opacity: 0, x: -10, filter: 'blur(4px)' }}
                  animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                  className="flex space-x-2 group"
                >
                    <span className="text-slate-700 select-none w-8 shrink-0">{i.toString().padStart(3, '0')}</span>
                    <span className={`leading-relaxed ${
                        isError ? 'text-red-400 font-bold' : 
                        isSystem ? 'text-cyan-400' : 
                        isAi ? 'text-emerald-400' : 
                        'text-slate-400'
                    }`}>
                        <span className="opacity-50 mr-1.5">{">"}</span>
                        {log}
                    </span>
                    {i === logs.length - 1 && (
                      <motion.span 
                        animate={{ opacity: [0, 1, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                        className="w-1.5 h-3 bg-emerald-500/50 inline-block ml-1 align-middle"
                      />
                    )}
                </motion.div>
              );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Terminal;