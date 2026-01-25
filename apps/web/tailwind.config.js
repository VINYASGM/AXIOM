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
                // AXIOM Brand Colors
                axiom: {
                    50: '#f0f4ff',
                    100: '#e0e8ff',
                    200: '#c7d4fe',
                    300: '#a4b8fc',
                    400: '#8093f8',
                    500: '#6366f1', // Primary
                    600: '#5046e5',
                    700: '#433bcd',
                    800: '#3730a3',
                    900: '#312e81',
                    950: '#1e1b4b',
                },
                // Confidence colors
                confidence: {
                    low: '#ef4444',    // Red - < 0.3
                    medium: '#f59e0b', // Amber - 0.3-0.7
                    high: '#22c55e',   // Green - 0.7-0.9
                    verified: '#06b6d4', // Cyan - > 0.9
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
