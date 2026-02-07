'use client';

export function AmbientLayer() {
    return (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {/* 1. Assumption Haze (Atmospheric Depth) */}
            <div className="absolute inset-0 bg-gradient-radial from-transparent to-[#050505] opacity-80" />

            {/* 2. Semantic Grid (Perspective Floor) */}
            <div
                className="absolute inset-0 opacity-[0.03]"
                style={{
                    backgroundImage: `linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)`,
                    backgroundSize: '40px 40px',
                    transform: 'perspective(1000px) rotateX(10deg) scale(1.5)',
                    transformOrigin: 'top center'
                }}
            />

            {/* 3. Floating Particles (Dust) - Optional Cinematic Touch */}
            <div className="absolute w-full h-full bg-[url('/noise.svg')] opacity-[0.02] mix-blend-overlay" />

            {/* 4. Vignette */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.4)_100%)]" />
        </div>
    );
}
