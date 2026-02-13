
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Box, Zap, Lock, Mail, User, ArrowRight, AlertCircle } from 'lucide-react';
import { ApiClient } from '../lib/api';

interface AuthScreenProps {
    onAuthenticated: () => void;
}

const AuthScreen: React.FC<AuthScreenProps> = ({ onAuthenticated }) => {
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [email, setEmail] = useState('');
    const [name, setName] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            if (mode === 'register') {
                await ApiClient.register(email, name, password);
            } else {
                await ApiClient.login(email, password);
            }
            onAuthenticated();
        } catch (err: any) {
            setError(err.message || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-[#010204] items-center justify-center overflow-hidden relative">
            {/* Background particles */}
            {[...Array(30)].map((_, i) => (
                <motion.div
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{
                        opacity: [0, 0.1, 0],
                        x: [Math.random() * window.innerWidth, Math.random() * window.innerWidth],
                        y: [Math.random() * window.innerHeight, Math.random() * window.innerHeight],
                    }}
                    transition={{ duration: Math.random() * 10 + 5, repeat: Infinity, ease: "linear" }}
                    className="absolute w-1 h-1 bg-sky-500 rounded-full blur-[1px]"
                />
            ))}

            <motion.div
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className="w-full max-w-md relative z-10"
            >
                {/* Logo */}
                <div className="text-center mb-12">
                    <motion.div
                        initial={{ scale: 0.8 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3, type: "spring", bounce: 0.4 }}
                        className="inline-flex p-5 bg-gradient-to-br from-sky-500 to-sky-700 rounded-[2rem] text-white shadow-[0_0_60px_rgba(14,165,233,0.3)] mb-6"
                    >
                        <Box size={36} />
                    </motion.div>
                    <h1 className="text-4xl font-black text-white tracking-tight">AXIOM</h1>
                    <p className="text-sm text-slate-600 mt-2 font-mono uppercase tracking-[0.3em]">
                        Autonomous Execution Platform
                    </p>
                </div>

                {/* Auth Card */}
                <div className="glass rounded-[2.5rem] p-10 border border-white/5 shadow-2xl shadow-black/50 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-sky-500/[0.03] to-transparent pointer-events-none" />

                    {/* Mode Toggle */}
                    <div className="flex bg-black/50 rounded-[1.5rem] p-1.5 mb-8 border border-white/5 relative z-10">
                        <button
                            onClick={() => { setMode('login'); setError(null); }}
                            className={`flex-1 py-3 rounded-[1.2rem] text-xs font-bold uppercase tracking-widest transition-all duration-500 ${mode === 'login'
                                    ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-lg'
                                    : 'text-slate-600 hover:text-slate-400'
                                }`}
                        >
                            Login
                        </button>
                        <button
                            onClick={() => { setMode('register'); setError(null); }}
                            className={`flex-1 py-3 rounded-[1.2rem] text-xs font-bold uppercase tracking-widest transition-all duration-500 ${mode === 'register'
                                    ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-lg'
                                    : 'text-slate-600 hover:text-slate-400'
                                }`}
                        >
                            Register
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5 relative z-10">
                        {/* Error */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs"
                            >
                                <AlertCircle size={14} />
                                {error}
                            </motion.div>
                        )}

                        {/* Email */}
                        <div className="relative group">
                            <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-sky-400 transition-colors" />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Email"
                                required
                                className="w-full bg-black/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-white placeholder:text-slate-700 focus:outline-none focus:border-sky-500/30 focus:ring-1 focus:ring-sky-500/20 transition-all font-mono"
                            />
                        </div>

                        {/* Name (register only) */}
                        {mode === 'register' && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="relative group"
                            >
                                <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-sky-400 transition-colors" />
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="Full Name"
                                    required
                                    className="w-full bg-black/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-white placeholder:text-slate-700 focus:outline-none focus:border-sky-500/30 focus:ring-1 focus:ring-sky-500/20 transition-all font-mono"
                                />
                            </motion.div>
                        )}

                        {/* Password */}
                        <div className="relative group">
                            <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-sky-400 transition-colors" />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Password"
                                required
                                minLength={6}
                                className="w-full bg-black/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-white placeholder:text-slate-700 focus:outline-none focus:border-sky-500/30 focus:ring-1 focus:ring-sky-500/20 transition-all font-mono"
                            />
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading}
                            className={`w-full py-4 rounded-2xl text-sm font-bold uppercase tracking-widest transition-all duration-500 flex items-center justify-center gap-3 relative overflow-hidden ${loading
                                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/20 cursor-wait'
                                    : 'bg-sky-500 text-white hover:bg-sky-400 shadow-[0_0_40px_rgba(14,165,233,0.3)] hover:shadow-[0_0_60px_rgba(14,165,233,0.5)]'
                                }`}
                        >
                            {loading ? (
                                <>
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                    >
                                        <Zap size={16} />
                                    </motion.div>
                                    Authenticating...
                                </>
                            ) : (
                                <>
                                    {mode === 'login' ? 'Access System' : 'Initialize Account'}
                                    <ArrowRight size={16} />
                                </>
                            )}
                            {loading && (
                                <motion.div
                                    className="absolute inset-0 bg-gradient-to-r from-sky-400/20 via-white/10 to-sky-400/20"
                                    animate={{ x: ['-100%', '100%'] }}
                                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                />
                            )}
                        </button>
                    </form>
                </div>

                <p className="text-center text-[10px] text-slate-700 mt-8 font-mono uppercase tracking-widest">
                    Semantic Development Environment v2.5
                </p>
            </motion.div>
        </div>
    );
};

export default AuthScreen;
