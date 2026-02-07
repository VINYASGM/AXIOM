'use client';

import { useCallback, useState, useEffect } from 'react';
import ReactFlow, {
    Background,
    Controls,
    Connection,
    Edge,
    Node,
    addEdge,
    useNodesState,
    useEdgesState,
    NodeTypes,
    EdgeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useSDEStore } from '@/store/sde';
import { AmbientLayer } from './layers/AmbientLayer';
import { IntentManifold } from './nodes/IntentManifold';
import { TensionCable } from './edges/TensionCable';
import { HolographicLens } from './tools/HolographicLens';
import { motion } from 'framer-motion';

// Register Custom Types
const nodeTypes: NodeTypes = {
    intent: IntentManifold, // Replaced IntentNode
};

const edgeTypes: EdgeTypes = {
    proof: TensionCable, // Replaced ProofEdge
};

// Initial Data for Demo (Advanced) - Fallback
const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

export function SpatialLedger() {
    const {
        setSelectedNodeId,
        setLensActive,
        isLensActive,
        graphNodes,
        graphEdges,
        fetchGraph
    } = useSDEStore();

    // Local state for React Flow interaction
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    // Fetch on Mount
    useEffect(() => {
        fetchGraph();
    }, [fetchGraph]);

    // Sync Store Data to React Flow State
    useEffect(() => {
        if (graphNodes.length > 0) {
            setNodes(graphNodes);
            setEdges(graphEdges);
        }
    }, [graphNodes, graphEdges, setNodes, setEdges]);

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    return (
        <div className="w-full h-full bg-[#030304] relative overflow-hidden font-sans">
            <AmbientLayer />

            {/* Background Grid using React Flow */}
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodeClick={(_, node) => setSelectedNodeId(node.id)}
                fitView
                className="z-10" // Canvas above AmbientLayer
                defaultEdgeOptions={{ type: 'proof', animated: true }}
            >
                <Controls className="bg-white/5 border border-white/5 text-gray-400 fill-gray-400" />
            </ReactFlow>

            {/* Lens Toggle */}
            <div className="absolute bottom-6 left-6 z-10 flex gap-4">
                <button
                    onClick={() => setLensActive(!isLensActive)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${isLensActive
                        ? 'bg-axiom-500/20 border-axiom-500 text-axiom-400 shadow-[0_0_15px_rgba(var(--axiom-500),0.3)]'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                        }`}
                >
                    {isLensActive ? 'Holographic Lens: ON' : 'Enable Lens'}
                </button>
            </div>

            {/* Empty State Overlay */}
            {nodes.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
                    <div className="text-center space-y-2 opacity-50">
                        <div className="text-4xl font-mono tracking-widest text-gray-600">VOID</div>
                        <div className="text-sm text-gray-500">No intents found in ledger. Add one via Chat.</div>
                    </div>
                </div>
            )}

            {/* Overlays */}
            <HolographicLens />
        </div>
    );
}
