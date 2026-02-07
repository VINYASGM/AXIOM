/**
 * useMemory - React hook for GraphRAG memory search
 * 
 * Provides unified vector + graph search with relationship visualization.
 */
import { useState, useCallback, useRef, useEffect } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export type MemoryTier = 'working' | 'project' | 'org';
export type RelationshipType =
    | 'implements'
    | 'depends_on'
    | 'supersedes'
    | 'refines'
    | 'tests'
    | 'documents';

export interface MemoryNode {
    id: string;
    content: string;
    nodeType: string;
    tier: MemoryTier;
    metadata: Record<string, string>;
    createdAt: string;
    sourceIvcuId?: string;
    projectId?: string;
    similarityScore?: number;
}

export interface MemoryEdge {
    id: string;
    sourceId: string;
    targetId: string;
    relationship: RelationshipType;
    weight: number;
    metadata: Record<string, string>;
}

export interface SearchResult {
    primaryNodes: MemoryNode[];
    relatedNodes: MemoryNode[];
    relationships: MemoryEdge[];
    queryTimeMs: number;
    bestScore: number;
}

export interface ImpactAnalysis {
    sourceNodeId: string;
    affectedCount: number;
    impactSeverity: 'low' | 'medium' | 'high';
    maxDepthReached: number;
    affectedNodes: Array<{
        id: string;
        contentPreview: string;
        nodeType: string;
        depth: number;
        relationship: string;
    }>;
}

export interface MemoryState {
    status: 'idle' | 'searching' | 'complete' | 'error';

    // Search results
    results: SearchResult | null;

    // Impact analysis
    impactAnalysis: ImpactAnalysis | null;

    // Query info
    lastQuery: string | null;
    searchTimeMs: number;

    // Error
    error: string | null;
}

export interface UseMemoryOptions {
    apiUrl?: string;
    projectId?: string;
    defaultTier?: MemoryTier;
    onResults?: (results: SearchResult) => void;
    onError?: (error: string) => void;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useMemory(options: UseMemoryOptions = {}) {
    const {
        apiUrl = '/api/v1/memory',
        projectId,
        defaultTier = 'project',
        onResults,
        onError,
    } = options;

    const [state, setState] = useState<MemoryState>({
        status: 'idle',
        results: null,
        impactAnalysis: null,
        lastQuery: null,
        searchTimeMs: 0,
        error: null,
    });

    const abortControllerRef = useRef<AbortController | null>(null);

    // Search memory
    const search = useCallback(async (
        query: string,
        options: {
            tier?: MemoryTier;
            nodeTypes?: string[];
            limit?: number;
            similarityThreshold?: number;
            includeRelated?: boolean;
            maxDepth?: number;
        } = {}
    ) => {
        const {
            tier = defaultTier,
            nodeTypes = [],
            limit = 10,
            similarityThreshold = 0.7,
            includeRelated = true,
            maxDepth = 2,
        } = options;

        // Cancel any existing search
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();

        setState(prev => ({
            ...prev,
            status: 'searching',
            lastQuery: query,
            error: null,
        }));

        const startTime = Date.now();

        try {
            const response = await fetch(`${apiUrl}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    project_id: projectId,
                    tier: tier === 'working' ? 1 : tier === 'project' ? 2 : 3,
                    node_types: nodeTypes,
                    limit,
                    similarity_threshold: similarityThreshold,
                    include_related: includeRelated,
                    max_depth: maxDepth,
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }

            const data = await response.json();

            const results: SearchResult = {
                primaryNodes: (data.primary_nodes || []).map(parseNode),
                relatedNodes: (data.related_nodes || []).map(parseNode),
                relationships: (data.relationships || []).map(parseEdge),
                queryTimeMs: data.query_time_ms || (Date.now() - startTime),
                bestScore: data.best_score || 0,
            };

            setState(prev => ({
                ...prev,
                status: 'complete',
                results,
                searchTimeMs: Date.now() - startTime,
            }));

            onResults?.(results);
            return results;

        } catch (error: any) {
            if (error.name === 'AbortError') {
                setState(prev => ({ ...prev, status: 'idle' }));
                return null;
            }

            const errorMsg = error.message || 'Search failed';
            setState(prev => ({
                ...prev,
                status: 'error',
                error: errorMsg,
            }));
            onError?.(errorMsg);
            return null;
        }
    }, [apiUrl, projectId, defaultTier, onResults, onError]);

    // Store a memory node
    const store = useCallback(async (
        content: string,
        nodeType: string,
        options: {
            tier?: MemoryTier;
            metadata?: Record<string, string>;
            sourceIvcuId?: string;
            relationships?: Array<{
                targetId: string;
                type: RelationshipType;
            }>;
        } = {}
    ) => {
        const {
            tier = defaultTier,
            metadata = {},
            sourceIvcuId,
            relationships = [],
        } = options;

        try {
            const response = await fetch(`${apiUrl}/store`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content,
                    node_type: nodeType,
                    tier: tier === 'working' ? 1 : tier === 'project' ? 2 : 3,
                    metadata,
                    source_ivcu_id: sourceIvcuId,
                    project_id: projectId,
                    relationships: relationships.map(r => ({
                        target_id: r.targetId,
                        type: relationshipToNumber(r.type),
                    })),
                }),
            });

            if (!response.ok) {
                throw new Error(`Store failed: ${response.statusText}`);
            }

            const data = await response.json();
            return { nodeId: data.node_id, success: data.success };

        } catch (error: any) {
            console.error('Store error:', error);
            return { nodeId: null, success: false };
        }
    }, [apiUrl, projectId, defaultTier]);

    // Get impact analysis
    const getImpact = useCallback(async (nodeId: string, maxDepth = 3) => {
        try {
            const response = await fetch(`${apiUrl}/impact`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    node_id: nodeId,
                    max_depth: maxDepth,
                }),
            });

            if (!response.ok) {
                throw new Error(`Impact analysis failed: ${response.statusText}`);
            }

            const data = await response.json();

            const impact: ImpactAnalysis = {
                sourceNodeId: data.source_node_id,
                affectedCount: data.affected_count,
                impactSeverity: data.impact_severity,
                maxDepthReached: data.max_depth_reached,
                affectedNodes: (data.affected_nodes || []).map((n: any) => ({
                    id: n.id,
                    contentPreview: n.content_preview,
                    nodeType: n.node_type,
                    depth: n.depth,
                    relationship: n.relationship,
                })),
            };

            setState(prev => ({
                ...prev,
                impactAnalysis: impact,
            }));

            return impact;

        } catch (error: any) {
            console.error('Impact analysis error:', error);
            return null;
        }
    }, [apiUrl]);

    // Add relationship
    const addRelationship = useCallback(async (
        sourceId: string,
        targetId: string,
        relationship: RelationshipType,
        weight = 1.0
    ) => {
        try {
            const response = await fetch(`${apiUrl}/relationship`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_id: sourceId,
                    target_id: targetId,
                    relationship: relationshipToNumber(relationship),
                    weight,
                }),
            });

            if (!response.ok) {
                throw new Error(`Add relationship failed: ${response.statusText}`);
            }

            const data = await response.json();
            return { edgeId: data.edge_id, success: data.success };

        } catch (error: any) {
            console.error('Add relationship error:', error);
            return { edgeId: null, success: false };
        }
    }, [apiUrl]);

    // Clear results
    const clear = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setState({
            status: 'idle',
            results: null,
            impactAnalysis: null,
            lastQuery: null,
            searchTimeMs: 0,
            error: null,
        });
    }, []);

    // Cleanup
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    // Computed values
    const isSearching = state.status === 'searching';
    const hasResults = state.results !== null && state.results.primaryNodes.length > 0;
    const totalNodes = state.results
        ? state.results.primaryNodes.length + state.results.relatedNodes.length
        : 0;

    return {
        // State
        ...state,

        // Computed
        isSearching,
        hasResults,
        totalNodes,

        // Actions
        search,
        store,
        getImpact,
        addRelationship,
        clear,
    };
}

// ============================================================================
// HELPERS
// ============================================================================

function parseNode(data: any): MemoryNode {
    return {
        id: data.id,
        content: data.content,
        nodeType: data.node_type,
        tier: parseTier(data.tier),
        metadata: data.metadata || {},
        createdAt: data.created_at || '',
        sourceIvcuId: data.source_ivcu_id,
        projectId: data.project_id,
        similarityScore: data.similarity_score,
    };
}

function parseEdge(data: any): MemoryEdge {
    return {
        id: data.id,
        sourceId: data.source_id,
        targetId: data.target_id,
        relationship: parseRelationship(data.relationship),
        weight: data.weight || 1.0,
        metadata: data.metadata || {},
    };
}

function parseTier(tier: string | number): MemoryTier {
    if (typeof tier === 'number') {
        return tier === 1 ? 'working' : tier === 3 ? 'org' : 'project';
    }
    return tier as MemoryTier;
}

function parseRelationship(rel: string | number): RelationshipType {
    if (typeof rel === 'number') {
        const mapping: Record<number, RelationshipType> = {
            1: 'implements',
            2: 'depends_on',
            3: 'supersedes',
            4: 'refines',
            5: 'tests',
            6: 'documents',
        };
        return mapping[rel] || 'depends_on';
    }
    return rel as RelationshipType;
}

function relationshipToNumber(rel: RelationshipType): number {
    const mapping: Record<RelationshipType, number> = {
        'implements': 1,
        'depends_on': 2,
        'supersedes': 3,
        'refines': 4,
        'tests': 5,
        'documents': 6,
    };
    return mapping[rel] || 2;
}
