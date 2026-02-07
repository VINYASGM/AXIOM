/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // AXIOM Design System
                canvas: '#09090B', // Zinc-950
                surface: '#18181B', // Zinc-900
                element: '#27272A', // Zinc-800
                border: '#3F3F46', // Zinc-700

                // Brand
                axiom: {
                    50: '#eef2ff',
                    100: '#e0e7ff',
                    200: '#c7d2fe',
                    300: '#a5b4fc',
                    400: '#818cf8',
                    500: '#6366f1', // Primary (Indigo)
                    600: '#4f46e5',
                    700: '#4338ca',
                    800: '#3730a3',
                    900: '#312e81',
                    950: '#1e1b4b',
                },

                // Semantic / PCC Status
                pcc: {
                    secure: '#10B981', // Emerald-500
                    warn: '#F59E0B',   // Amber-500
                    danger: '#EF4444', // Red-500
                    verify: '#06b6d4', // Cyan-500
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'glow': 'glow 2s ease-in-out infinite alternate',
            },
            keyframes: {
                glow: {
                    '0%': { boxShadow: '0 0 5px rgba(99, 102, 241, 0.5)' },
                    '100%': { boxShadow: '0 0 20px rgba(99, 102, 241, 0.8)' },
                },
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'axiom-gradient': 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%)',
            },
        },
    },
    plugins: [],
};
