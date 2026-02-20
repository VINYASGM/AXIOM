import React from 'react';
import { useAxiomStore } from '../store/axiom';
import type { ImplementationPlan } from '../types/ivcu';

export default function ReasoningTrace() {
    const currentIVCU = useAxiomStore(s => s.currentIVCU);
    const plan: ImplementationPlan | null | undefined = currentIVCU?.implementation_plan ?? null;

    if (!plan) {
        return <div className="text-gray-500 italic p-4">No implementation plan available for this intent.</div>;
    }

    if (plan.summary === 'INSUFFICIENT_INPUT') {
        return <div className="text-amber-500 p-4">Plan could not be generated - please provide a more detailed intent.</div>;
    }

    return (
        <div className="reasoning-trace space-y-6 text-sm text-gray-200">
            <div className="border-b border-gray-800 pb-2">
                <h3 className="text-lg font-medium text-white mb-1">Implementation Plan</h3>
                <p className="text-gray-400">{plan.summary}</p>
            </div>

            <section>
                <h4 className="text-xs uppercase tracking-wider text-gray-500 mb-2 font-semibold">Execution Steps</h4>
                <ol className="list-decimal list-outside ml-4 space-y-1">
                    {plan.steps.map((s, i) => <li key={i} className="pl-1">{s}</li>)}
                </ol>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <section>
                    <h4 className="text-xs uppercase tracking-wider text-gray-500 mb-2 font-semibold">Architecture Decisions</h4>
                    <ul className="list-disc list-outside ml-4 space-y-1">
                        {plan.architecture.map((a, i) => <li key={i} className="pl-1 text-blue-300">{a}</li>)}
                    </ul>
                </section>

                <section>
                    <h4 className="text-xs uppercase tracking-wider text-gray-500 mb-2 font-semibold">Edge Cases</h4>
                    <ul className="list-disc list-outside ml-4 space-y-1">
                        {plan.edge_cases && plan.edge_cases.length > 0
                            ? plan.edge_cases.map((e, i) => <li key={i} className="pl-1 text-amber-300">{e}</li>)
                            : <li className="text-gray-600 italic">None identified</li>
                        }
                    </ul>
                </section>
            </div>

            {plan.key_decisions && plan.key_decisions.length > 0 && (
                <section>
                    <h4 className="text-xs uppercase tracking-wider text-gray-500 mb-3 font-semibold">Key Technical Decisions</h4>
                    <div className="space-y-3">
                        {plan.key_decisions.map((d, i) => (
                            <div className="bg-gray-800/50 rounded p-3 border border-gray-800" key={i}>
                                <strong className="block text-blue-400 mb-1">{d.decision}</strong>
                                <p className="mb-1 text-gray-300">{d.rationale}</p>
                                {d.tradeoffs && <p className="text-xs text-gray-500 mt-2"><em className="text-gray-400">Tradeoffs:</em> {d.tradeoffs}</p>}
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {plan.estimated_effort && (
                <section className="flex items-center space-x-2 pt-2 border-t border-gray-800">
                    <h4 className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Est. Effort:</h4>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${plan.estimated_effort.complexity === 'high' ? 'bg-red-900/40 text-red-200' :
                            plan.estimated_effort.complexity === 'medium' ? 'bg-amber-900/40 text-amber-200' :
                                'bg-green-900/40 text-green-200'
                        }`}>
                        {plan.estimated_effort.complexity.toUpperCase()}
                    </span>
                    {plan.estimated_effort.hours && (
                        <span className="text-xs text-gray-500">({plan.estimated_effort.hours}h)</span>
                    )}
                </section>
            )}
        </div>
    );
}
