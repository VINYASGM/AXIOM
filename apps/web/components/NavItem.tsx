import React from 'react';

interface NavItemProps {
    active: boolean;
    icon: React.ReactNode;
    onClick?: () => void;
    label: string;
}

const NavItem: React.FC<NavItemProps> = ({ active, icon, onClick, label }) => (
    <button
        onClick={onClick}
        className={`group relative p-3 rounded-2xl transition-all duration-500 ${active
            ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-[0_0_30px_rgba(14,165,233,0.15)]'
            : 'text-slate-700 hover:text-slate-400 hover:bg-white/5'
            }`}
        title={label}
    >
        {icon}

        <div className="absolute left-full ml-4 px-3 py-2 bg-[#010204] border border-white/10 text-[11px] font-bold text-slate-300 rounded-xl opacity-0 group-hover:opacity-100 transition-all transform scale-95 group-hover:scale-100 group-hover:translate-x-1 whitespace-nowrap z-[100] pointer-events-none shadow-2xl backdrop-blur-3xl border-l-2 border-l-sky-500">
            {label}
        </div>

        {active && (
            <div
                className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-8 bg-sky-500 rounded-full shadow-[0_0_15px_#0ea5e9]"
            />
        )}
    </button>
);

export default NavItem;
