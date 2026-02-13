import React from 'react';

interface TelemetryItemProps {
    label: string;
    value: string;
    color: string;
    icon: React.ReactNode;
}

const TelemetryItem: React.FC<TelemetryItemProps> = ({ label, value, color, icon }) => (
    <div className="flex items-center justify-between text-[11px] group">
        <div className="flex items-center space-x-3 text-slate-500">
            <div className="p-2 rounded-xl bg-white/5 border border-white/5 group-hover:border-sky-500/40 group-hover:bg-sky-500/5 transition-all duration-500">
                {icon}
            </div>
            <span className="uppercase tracking-[0.3em] mono text-[10px] font-semibold group-hover:text-slate-300 transition-colors">{label}</span>
        </div>
        <span className={`${color} mono font-bold group-hover:scale-110 transition-transform`}>{value}</span>
    </div>
);

export default TelemetryItem;
