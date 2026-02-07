import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'destructive' | 'ghost';

interface ButtonProps extends Omit<HTMLMotionProps<"button">, 'children'> {
  variant?: ButtonVariant;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  children?: React.ReactNode;
  active?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading,
  children,
  active,
  className = '',
  ...props
}) => {
  const baseStyles = "relative flex items-center justify-center font-bold mono uppercase tracking-[0.2em] transition-all duration-500 disabled:opacity-30 disabled:cursor-not-allowed overflow-hidden whitespace-nowrap select-none";
  
  const sizeStyles = {
    sm: "px-4 py-2 text-[9px] rounded-xl gap-2",
    md: "px-6 py-3 text-[10px] rounded-2xl gap-2.5",
    lg: "px-10 py-5 text-[11px] rounded-[1.2rem] gap-3.5",
    xl: "px-14 py-6 text-[12px] rounded-[1.8rem] gap-4",
  };

  const variantStyles = {
    primary: "bg-emerald-500 text-slate-950 border border-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_40px_rgba(16,185,129,0.5)] hover:bg-emerald-400",
    secondary: "glass border border-white/10 text-slate-300 hover:text-white hover:bg-white/10 hover:border-white/25 shadow-2xl",
    tertiary: "bg-transparent border border-white/5 text-slate-600 hover:text-slate-200 hover:border-white/10 hover:bg-white/[0.02]",
    destructive: "bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500 hover:text-slate-950 hover:shadow-[0_0_35px_rgba(239,68,68,0.4)]",
    ghost: "bg-transparent text-slate-700 hover:text-emerald-400 p-2 hover:bg-emerald-500/5",
  };

  const activeStyles = active ? "ring-2 ring-emerald-500/40 bg-emerald-500/10 border-emerald-500/40 text-emerald-400" : "";

  return (
    <motion.button
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.97, y: 0 }}
      transition={{ type: "spring", stiffness: 400, damping: 15 }}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${activeStyles} ${className}`}
      {...props}
    >
      {/* Dynamic Interaction Backgrounds */}
      {variant === 'primary' && !loading && (
        <motion.div
          className="absolute inset-0 z-0 bg-gradient-to-r from-transparent via-white/40 to-transparent"
          initial={{ x: '-100%' }}
          animate={{ x: '100%' }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear", repeatDelay: 1 }}
        />
      )}
      
      {variant === 'destructive' && (
        <motion.div
          className="absolute inset-0 z-0 bg-red-500/5"
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}

      <div className="relative z-10 flex items-center justify-center gap-inherit">
        {loading ? (
          <div className="flex items-center gap-2">
            <motion.div 
              animate={{ x: [-10, 10, -10] }}
              transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
              className="w-1.5 h-1.5 bg-current rounded-full"
            />
            <span className="opacity-70">Processing</span>
          </div>
        ) : (
          <>
            {Icon && iconPosition === 'left' && <Icon size={size === 'sm' ? 14 : 18} />}
            <span>{children}</span>
            {Icon && iconPosition === 'right' && <Icon size={size === 'sm' ? 14 : 18} />}
          </>
        )}
      </div>

      {/* Internal Kinetic Pulse */}
      {active && (
        <motion.div
          layoutId="active-highlight"
          className="absolute inset-0 bg-white/5 -z-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        />
      )}
    </motion.button>
  );
};

export default Button;