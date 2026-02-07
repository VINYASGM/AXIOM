import { create } from 'zustand';
import { Node, Edge, Viewport } from 'reactflow';

interface SDEState {
    // Canvas State
    viewport: Viewport;
    setViewport: (viewport: Viewport) => void;

    // Selection
    selectedNodeId: string | null;
    setSelectedNodeId: (id: string | null) => void;

    // Holographic Lens
    isLensActive: boolean;
    lensTargetId: string | null;
    setLensActive: (active: boolean) => void;
    setLensTarget: (nodeId: string | null) => void;

    // Filters/Layers
    showImpliedEdges: boolean;
    toggleImpliedEdges: () => void;
    showVerifiedOnly: boolean;
    toggleVerifiedOnly: () => void;

    // Graph Data
    graphNodes: Node[];
    graphEdges: Edge[];
    fetchGraph: () => Promise<void>;
}

export const useSDEStore = create<SDEState>((set) => ({
    viewport: { x: 0, y: 0, zoom: 1 },
    setViewport: (viewport) => set({ viewport }),

    selectedNodeId: null,
    setSelectedNodeId: (id) => set({ selectedNodeId: id }),

    isLensActive: false,
    lensTargetId: null,
    setLensActive: (active) => set({ isLensActive: active }),
    setLensTarget: (target) => set({ lensTargetId: target }),

    showImpliedEdges: false,
    toggleImpliedEdges: () => set((state) => ({ showImpliedEdges: !state.showImpliedEdges })),

    showVerifiedOnly: false,
    toggleVerifiedOnly: () => set((state) => ({ showVerifiedOnly: !state.showVerifiedOnly })),

    graphNodes: [],
    graphEdges: [],
    fetchGraph: async () => {
        try {
            const res = await fetch('/api/v1/graph');
            const data = await res.json();

            // Map API nodes to React Flow nodes with Grid Layout
            const mappedNodes: Node[] = data.nodes.map((n: any, i: number) => ({
                id: n.id,
                type: 'intent', // Maps to IntentManifold
                position: {
                    x: (i % 3) * 500 + 100, // 3 columns
                    y: Math.floor(i / 3) * 400 + 150
                },
                data: {
                    label: n.label,
                    description: n.description,
                    confidence: n.confidence,
                    status: n.status,
                    constraints: n.constraints,
                    complexity: n.complexity
                }
            }));

            const mappedEdges: Edge[] = data.edges.map((e: any) => ({
                id: e.id,
                source: e.source,
                target: e.target,
                type: 'proof', // Maps to TensionCable
                data: { status: e.status, label: e.type }
            }));

            // If empty (no backend data), keep initial mock data? 
            // Better to show empty state or just the mapped response.
            // If response is empty, we might want to seed one "Start Here" node?
            // For now, just set what we get.

            set({ graphNodes: mappedNodes, graphEdges: mappedEdges });
        } catch (e) {
            console.error("Failed to fetch SDE graph", e);
        }
    }
}));
