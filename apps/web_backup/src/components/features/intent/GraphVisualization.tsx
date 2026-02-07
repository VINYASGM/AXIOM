'use client';

import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useAxiomStore } from '@/store/axiom';
import { Loader2, RefreshCw } from 'lucide-react';

const nodeTypes = {
    // We can define custom node types here if needed, 
    // for now using default with styling
};

// Map backend node types to colors
const getNodeColor = (type: string) => {
    switch (type) {
        case 'intent': return '#a855f7'; // Purple
        case 'code': return '#3b82f6';   // Blue
        case 'constraint': return '#ef4444'; // Red
        case 'decision': return '#f59e0b'; // Amber
        case 'test': return '#22c55e'; // Green
        case 'dependency': return '#64748b'; // Slate
        default: return '#71717a'; // Zinc
    }
};

export function GraphVisualization() {
    const { token, currentProject } = useAxiomStore();
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [loading, setLoading] = useState(true);

    const fetchGraph = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            // Call Go backend which proxies to AI service
            const res = await fetch('/api/v1/graph', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!res.ok) throw new Error('Failed to fetch graph');

            const data = await res.json();

            // Transform to ReactFlow format
            const flowNodes: Node[] = data.primary_nodes.map((n: any, i: number) => ({
                id: n.id,
                type: 'default',
                data: { label: `${n.node_type}: ${n.content.substring(0, 20)}...` },
                position: { x: (i % 5) * 200, y: Math.floor(i / 5) * 150 }, // Simple grid layout
                style: {
                    background: '#18181b',
                    color: '#fff',
                    border: '1px solid ' + getNodeColor(n.node_type),
                    width: 180,
                    fontSize: '12px'
                },
            }));

            const flowEdges: Edge[] = data.relationships.map((e: any) => ({
                id: e.id,
                source: e.source_id,
                target: e.target_id,
                label: e.relationship,
                type: 'smoothstep',
                animated: true,
                style: { stroke: '#52525b' },
                labelStyle: { fill: '#a1a1aa', fontSize: 10 },
                markerEnd: { type: MarkerType.ArrowClosed, color: '#52525b' },
            }));

            setNodes(flowNodes);
            setEdges(flowEdges);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token, setNodes, setEdges]); // Removed invalid dependencies

    useEffect(() => {
        fetchGraph();
    }, [fetchGraph]);

    return (
        <div className="h-full w-full bg-black/40 relative rounded-xl overflow-hidden border border-white/5">
            <div className="absolute top-4 right-4 z-10">
                <button
                    onClick={fetchGraph}
                    className="p-2 bg-black/50 hover:bg-white/10 rounded-lg text-white/50 hover:text-white transition-colors border border-white/5"
                    disabled={loading}
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                </button>
            </div>

            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                fitView
                className="bg-transparent"
                minZoom={0.1}
            >
                <Background color="#333" gap={20} size={1} />
                <Controls className="bg-black/50 border-white/10 fill-white" />
            </ReactFlow>

            {nodes.length === 0 && !loading && (
                <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
                    No graph data available
                </div>
            )}
        </div>
    );
}
