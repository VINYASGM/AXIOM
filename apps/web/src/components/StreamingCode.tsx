'use client';

/**
 * StreamingCode - Component for displaying streaming code generation
 * 
 * Shows real-time token streaming with syntax highlighting placeholder,
 * typing animation, and cursor effect.
 */
import React, { useEffect, useRef, useState } from 'react';

// ============================================================================
// TYPES
// ============================================================================

interface StreamingCodeProps {
    code: string;
    language?: string;
    isStreaming?: boolean;
    className?: string;
    showLineNumbers?: boolean;
    onComplete?: () => void;
}

// ============================================================================
// STREAMING CODE DISPLAY
// ============================================================================

export function StreamingCode({
    code,
    language = 'python',
    isStreaming = false,
    className = '',
    showLineNumbers = true,
    onComplete,
}: StreamingCodeProps) {
    const codeRef = useRef<HTMLPreElement>(null);
    const [showCursor, setShowCursor] = useState(true);

    // Blink cursor effect
    useEffect(() => {
        if (!isStreaming) {
            setShowCursor(false);
            return;
        }

        const interval = setInterval(() => {
            setShowCursor(prev => !prev);
        }, 530);

        return () => clearInterval(interval);
    }, [isStreaming]);

    // Auto-scroll to bottom during streaming
    useEffect(() => {
        if (isStreaming && codeRef.current) {
            codeRef.current.scrollTop = codeRef.current.scrollHeight;
        }
    }, [code, isStreaming]);

    // Notify when streaming completes
    useEffect(() => {
        if (!isStreaming && code.length > 0) {
            onComplete?.();
        }
    }, [isStreaming, code.length, onComplete]);

    // Split code into lines
    const lines = code.split('\n');

    // Basic syntax highlighting patterns
    const highlightLine = (line: string): React.ReactNode => {
        // Keywords
        const keywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif',
            'for', 'while', 'try', 'except', 'async', 'await', 'with', 'as',
            'const', 'let', 'var', 'function', 'export', 'import', 'default'];

        // Simple token-based highlighting
        const tokens = line.split(/(\s+|[(){}[\],.:;])/);

        return tokens.map((token, i) => {
            // Comments
            if (token.startsWith('#') || token.startsWith('//')) {
                return <span key={i} className="text-zinc-500">{token}</span>;
            }
            // Strings
            if (token.match(/^["'`].*["'`]$/)) {
                return <span key={i} className="text-emerald-400">{token}</span>;
            }
            // Keywords
            if (keywords.includes(token)) {
                return <span key={i} className="text-purple-400">{token}</span>;
            }
            // Functions
            if (token.match(/^\w+$/) && tokens[i + 1] === '(') {
                return <span key={i} className="text-blue-400">{token}</span>;
            }
            // Numbers
            if (token.match(/^\d+$/)) {
                return <span key={i} className="text-amber-400">{token}</span>;
            }
            // Default
            return <span key={i}>{token}</span>;
        });
    };

    return (
        <div className={`relative bg-zinc-900 rounded-xl overflow-hidden ${className}`}>
            {/* Header bar */}
            <div className="flex items-center justify-between px-4 py-2 bg-zinc-800/50 border-b border-zinc-700">
                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500/80" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                        <div className="w-3 h-3 rounded-full bg-green-500/80" />
                    </div>
                    <span className="text-xs text-zinc-500 ml-2">{language}</span>
                </div>

                {isStreaming && (
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                        <span className="text-xs text-blue-400">Generating...</span>
                    </div>
                )}
            </div>

            {/* Code area */}
            <pre
                ref={codeRef}
                className="p-4 overflow-auto max-h-[500px] font-mono text-sm text-zinc-100"
                style={{ tabSize: 2 }}
            >
                <code>
                    {lines.map((line, lineIndex) => (
                        <div key={lineIndex} className="flex">
                            {showLineNumbers && (
                                <span className="select-none w-8 text-right pr-4 text-zinc-600">
                                    {lineIndex + 1}
                                </span>
                            )}
                            <span className="flex-1">
                                {highlightLine(line)}
                                {/* Cursor at end of last line during streaming */}
                                {isStreaming && lineIndex === lines.length - 1 && (
                                    <span
                                        className={`inline-block w-2 h-4 ml-0.5 -mb-0.5 ${showCursor ? 'bg-blue-400' : 'bg-transparent'
                                            }`}
                                    />
                                )}
                            </span>
                        </div>
                    ))}
                </code>
            </pre>

            {/* Empty state */}
            {code.length === 0 && !isStreaming && (
                <div className="p-8 text-center text-zinc-500">
                    <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <p>Code will appear here</p>
                </div>
            )}
        </div>
    );
}

// ============================================================================
// CODE DIFF VIEW
// ============================================================================

interface CodeDiffProps {
    oldCode: string;
    newCode: string;
    language?: string;
    className?: string;
}

export function CodeDiff({
    oldCode,
    newCode,
    language = 'python',
    className = '',
}: CodeDiffProps) {
    const oldLines = oldCode.split('\n');
    const newLines = newCode.split('\n');

    // Simple diff - show all lines with add/remove markers
    const diffLines: Array<{
        type: 'add' | 'remove' | 'same';
        content: string;
        lineNumber: number | null;
    }> = [];

    // Very simple diff algorithm
    const maxLines = Math.max(oldLines.length, newLines.length);
    for (let i = 0; i < maxLines; i++) {
        const oldLine = oldLines[i];
        const newLine = newLines[i];

        if (oldLine === newLine) {
            diffLines.push({ type: 'same', content: newLine || '', lineNumber: i + 1 });
        } else {
            if (oldLine !== undefined) {
                diffLines.push({ type: 'remove', content: oldLine, lineNumber: null });
            }
            if (newLine !== undefined) {
                diffLines.push({ type: 'add', content: newLine, lineNumber: i + 1 });
            }
        }
    }

    return (
        <div className={`bg-zinc-900 rounded-xl overflow-hidden ${className}`}>
            <div className="px-4 py-2 bg-zinc-800/50 border-b border-zinc-700">
                <span className="text-xs text-zinc-500">Diff</span>
            </div>
            <pre className="p-4 overflow-auto max-h-[400px] font-mono text-sm">
                <code>
                    {diffLines.map((line, i) => (
                        <div
                            key={i}
                            className={`flex ${line.type === 'add' ? 'bg-emerald-500/10' :
                                    line.type === 'remove' ? 'bg-red-500/10' : ''
                                }`}
                        >
                            <span className={`w-6 text-center select-none ${line.type === 'add' ? 'text-emerald-400' :
                                    line.type === 'remove' ? 'text-red-400' : 'text-zinc-600'
                                }`}>
                                {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}
                            </span>
                            <span className={`flex-1 ${line.type === 'add' ? 'text-emerald-300' :
                                    line.type === 'remove' ? 'text-red-300' : 'text-zinc-100'
                                }`}>
                                {line.content}
                            </span>
                        </div>
                    ))}
                </code>
            </pre>
        </div>
    );
}

// ============================================================================
// CANDIDATE TABS
// ============================================================================

interface Candidate {
    id: string;
    code: string;
    confidence: number;
    verified?: boolean;
}

interface CandidateTabsProps {
    candidates: Candidate[];
    selectedId: string | null;
    onSelect: (id: string) => void;
    className?: string;
}

export function CandidateTabs({
    candidates,
    selectedId,
    onSelect,
    className = '',
}: CandidateTabsProps) {
    return (
        <div className={`flex gap-2 overflow-x-auto pb-2 ${className}`}>
            {candidates.map((candidate, index) => (
                <button
                    key={candidate.id}
                    onClick={() => onSelect(candidate.id)}
                    className={`
            flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap
            transition-all
            ${selectedId === candidate.id
                            ? 'bg-blue-500 text-white'
                            : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                        }
          `}
                >
                    <span>Candidate {index + 1}</span>

                    {/* Confidence badge */}
                    <span className={`text-xs px-1.5 py-0.5 rounded ${candidate.confidence >= 0.9 ? 'bg-emerald-500/20 text-emerald-400' :
                            candidate.confidence >= 0.7 ? 'bg-blue-500/20 text-blue-400' :
                                'bg-amber-500/20 text-amber-400'
                        }`}>
                        {Math.round(candidate.confidence * 100)}%
                    </span>

                    {/* Verified indicator */}
                    {candidate.verified !== undefined && (
                        candidate.verified ? (
                            <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                        ) : (
                            <svg className="w-4 h-4 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                        )
                    )}
                </button>
            ))}
        </div>
    );
}

export default StreamingCode;
