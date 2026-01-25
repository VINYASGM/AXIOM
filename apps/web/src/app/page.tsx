'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { IntentCanvas } from '@/components/IntentCanvas';
import { ReviewPanel } from '@/components/ReviewPanel';
import { ConfidenceIndicator } from '@/components/ConfidenceIndicator';
import { IntelligenceDashboard } from '@/components/IntelligenceDashboard';
import { GenerationStatsPanel } from '@/components/GenerationStatsPanel';
import { useAxiomStore } from '@/store/axiom';
import { Sparkles, Zap, Shield, Brain } from 'lucide-react';

export default function Home() {
    const { currentIVCU, isGenerating, setToken } = useAxiomStore();

    useEffect(() => {
        // Auto-login for dev environment
        const login = async () => {
            try {
                const res = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: 'dev@axiom.local',
                        password: 'password'
                    })
                });
                if (res.ok) {
                    const data = await res.json();
                    setToken(data.token);
                    console.log('Dev Login Successful');
                }
            } catch (e) {
                console.error('Dev Login Failed', e);
            }
        };
        login();
    }, [setToken]);

    return (
        <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-axiom-950">
            {/* Header */}
            <header className="border-b border-white/10 bg-black/30 backdrop-blur-xl">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <motion.div
                            className="w-10 h-10 rounded-xl bg-axiom-gradient flex items-center justify-center"
                            animate={{ rotate: isGenerating ? 360 : 0 }}
                            transition={{ duration: 2, repeat: isGenerating ? Infinity : 0, ease: "linear" }}
                        >
                            <Sparkles className="w-5 h-5 text-white" />
                        </motion.div>
                        <div>
                            <h1 className="text-xl font-bold text-white">AXIOM</h1>
                            <p className="text-xs text-gray-400">Semantic Development Environment</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <Shield className="w-4 h-4 text-green-400" />
                            <span>Verified</span>
                        </div>
                        {currentIVCU && (
                            <ConfidenceIndicator confidence={currentIVCU.confidence} />
                        )}
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <div className="container mx-auto px-6 py-8">
                {/* Hero Section */}
                <motion.section
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-12"
                >
                    <h2 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-axiom-gradient mb-4">
                        Express Intent. Generate Verified Code.
                    </h2>
                    <p className="text-gray-400 max-w-2xl mx-auto text-lg">
                        Describe what you want in natural language. AXIOM verifies and generates
                        production-ready code with confidence scores.
                    </p>
                </motion.section>

                {/* Features Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    <FeatureCard
                        icon={<Brain className="w-6 h-6" />}
                        title="Intent-First"
                        description="Code derives from intent, not vice versa"
                    />
                    <FeatureCard
                        icon={<Shield className="w-6 h-6" />}
                        title="Verification-Gated"
                        description="Every output passes verification before you see it"
                    />
                    <FeatureCard
                        icon={<Zap className="w-6 h-6" />}
                        title="Confidence-Scored"
                        description="Know exactly how reliable each generation is"
                    />
                </div>

                {/* Main Workspace */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <IntentCanvas />
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <ReviewPanel />
                    </motion.div>

                </div>

                {/* Intelligence Layer Dashboards */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-12">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="lg:col-span-2"
                    >
                        <IntelligenceDashboard />
                    </motion.div>
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                    >
                        <GenerationStatsPanel />
                    </motion.div>
                </div>
            </div>

            {/* Footer */}
            <footer className="border-t border-white/10 mt-20">
                <div className="container mx-auto px-6 py-6 text-center text-gray-500 text-sm">
                    <p>AXIOM v0.1.0 | Phase 1: Foundation</p>
                </div>
            </footer>
        </main >
    );
}

function FeatureCard({
    icon,
    title,
    description
}: {
    icon: React.ReactNode;
    title: string;
    description: string;
}) {
    return (
        <motion.div
            whileHover={{ scale: 1.02, y: -2 }}
            className="glass rounded-2xl p-6 cursor-default"
        >
            <div className="w-12 h-12 rounded-xl bg-axiom-500/20 flex items-center justify-center text-axiom-400 mb-4">
                {icon}
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
            <p className="text-gray-400 text-sm">{description}</p>
        </motion.div>
    );
}
