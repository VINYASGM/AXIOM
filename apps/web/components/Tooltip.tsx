
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

const Tooltip: React.FC<TooltipProps> = ({ content, children, position = 'top' }) => {
  const [isVisible, setIsVisible] = useState(false);

  const positionStyles = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-4",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-4",
    left: "right-full top-1/2 -translate-y-1/2 mr-4",
    right: "left-full top-1/2 -translate-y-1/2 ml-4",
  };

  return (
    <div 
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: position === 'top' ? 8 : -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
            className={`absolute z-[200] ${positionStyles[position]} pointer-events-none`}
          >
            <div className="bg-[#0e1117] px-6 py-5 rounded-[1.5rem] border border-white/10 shadow-[0_30px_60px_-15px_rgba(0,0,0,0.8)] min-w-[280px] max-w-[360px] backdrop-blur-3xl overflow-visible">
              <div className="relative z-10">
                {content}
              </div>
              {/* Tooltip Arrow - Glossy Finish */}
              <div className={`absolute w-3 h-3 bg-[#0e1117] border-white/10 rotate-45 -z-10 ${
                position === 'top' ? 'bottom-[-6px] left-1/2 -translate-x-1/2 border-b border-r' :
                position === 'bottom' ? 'top-[-6px] left-1/2 -translate-x-1/2 border-t border-l' :
                position === 'left' ? 'right-[-6px] top-1/2 -translate-y-1/2 border-t border-r' :
                'left-[-6px] top-1/2 -translate-y-1/2 border-b border-l'
              }`} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Tooltip;
