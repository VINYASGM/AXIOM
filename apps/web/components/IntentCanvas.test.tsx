/**
 * @vitest-environment jsdom
 * @axiom-test-suite IntentCanvas.v2
 * Logic Probes: Undo/Redo, Async Orchestration, Tier Validation
 */

import React from 'react';
import { render, screen, fireEvent, act, cleanup, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// ─── Mock framer-motion ──────────────────────────────────────
// NOTE: vi.mock factories are hoisted. We use `await vi.importActual` for React
// inside framer-motion only — this is safe because framer-motion is not React itself.
vi.mock('framer-motion', async () => {
  const R = await vi.importActual<typeof import('react')>('react');

  const FakeMotion = R.forwardRef(({ children, ...props }: any, ref: any) => {
    const {
      initial, animate, exit, variants, transition,
      whileHover, whileTap, whileFocus, whileDrag, whileInView,
      layout, layoutId, layoutScroll, layoutRoot,
      onAnimationStart, onAnimationComplete, onUpdate, onDragStart, onDragEnd, onDrag,
      drag, dragControls, dragListener, dragConstraints, dragElastic, dragMomentum, dragTransition, dragPropagation,
      onPan, onPanStart, onPanEnd, onPanSessionStart,
      viewport,
      style: rawStyle,
      ...domProps
    } = props as any;

    let safeStyle: Record<string, any> | undefined;
    if (rawStyle && typeof rawStyle === 'object') {
      safeStyle = {};
      for (const [key, val] of Object.entries(rawStyle)) {
        if (val && typeof val === 'object' && typeof (val as any).get === 'function') {
          safeStyle[key] = (val as any).get();
        } else {
          safeStyle[key] = val;
        }
      }
    }

    return R.createElement('div', { ...domProps, style: safeStyle, ref }, children);
  });

  const motionProxy = new Proxy({}, {
    get: (_target: any, _prop: any) => FakeMotion,
  });

  return {
    __esModule: true,
    motion: motionProxy,
    AnimatePresence: ({ children }: any) => R.createElement(R.Fragment, null, children),
    LayoutGroup: ({ children }: any) => R.createElement(R.Fragment, null, children),
    useMotionValue: (v: number) => ({ get: () => v, set: () => { }, onChange: () => () => { } }),
    useSpring: (v: number) => ({ get: () => v, set: () => { }, onChange: () => () => { } }),
    useTransform: (_v: any) => ({ get: () => 0, set: () => { }, onChange: () => () => { } }),
  };
});

// ─── Mock lucide-react with explicit named exports ───────────
// All icon factories are defined inline to avoid hoisting issues.
vi.mock('lucide-react', async () => {
  const R = await vi.importActual<typeof import('react')>('react');
  const mkIcon = (name: string) => {
    const Icon = (props: any) => R.createElement('span', { 'data-testid': `icon-${name}`, ...props });
    Icon.displayName = name;
    return Icon;
  };
  return {
    __esModule: true,
    Send: mkIcon('Send'),
    Wand2: mkIcon('Wand2'),
    Undo2: mkIcon('Undo2'),
    Redo2: mkIcon('Redo2'),
    Activity: mkIcon('Activity'),
    CheckCircle2: mkIcon('CheckCircle2'),
    Clock: mkIcon('Clock'),
    AlertCircle: mkIcon('AlertCircle'),
    ChevronRight: mkIcon('ChevronRight'),
    ChevronDown: mkIcon('ChevronDown'),
    ChevronUp: mkIcon('ChevronUp'),
    Info: mkIcon('Info'),
    Image: mkIcon('Image'),
    X: mkIcon('X'),
    Sparkles: mkIcon('Sparkles'),
    Layers: mkIcon('Layers'),
    Terminal: mkIcon('Terminal'),
    ShieldCheck: mkIcon('ShieldCheck'),
    Zap: mkIcon('Zap'),
    Box: mkIcon('Box'),
    Cpu: mkIcon('Cpu'),
    Fingerprint: mkIcon('Fingerprint'),
    Save: mkIcon('Save'),
    History: mkIcon('History'),
    Code: mkIcon('Code'),
    Copy: mkIcon('Copy'),
    Lock: mkIcon('Lock'),
    XCircle: mkIcon('XCircle'),
    DollarSign: mkIcon('DollarSign'),
    LucideIcon: mkIcon('LucideIcon'),
  };
});

// Mock API client
vi.mock('../lib/api', () => ({
  ApiClient: {
    speculateIntent: vi.fn().mockResolvedValue({ paths: [] }),
  },
}));

// Mock tree-sitter
vi.mock('../lib/tree-sitter', () => ({
  initTreeSitter: vi.fn().mockResolvedValue(undefined),
  getParser: vi.fn().mockResolvedValue(null),
  SupportedLanguage: { PYTHON: 'python', JAVASCRIPT: 'javascript', TYPESCRIPT: 'typescript' },
}));

// Mock learnerStore to avoid zustand issues in test
vi.mock('../src/store/learnerStore', () => ({
  useLearnerStore: Object.assign(vi.fn().mockReturnValue({
    recordEvent: vi.fn(),
    skills: {},
    profile: null,
  }), {
    getState: vi.fn().mockReturnValue({
      recordEvent: vi.fn(),
      skills: {},
      profile: null,
    }),
  }),
  SkillDomain: {
    ArchitecturalReasoning: 'architectural_reasoning',
    CodeGeneration: 'code_generation',
    SecurityAwareness: 'security_awareness',
  },
}));

// Mock AdaptiveWrapper to just render children
vi.mock('./AdaptiveWrapper', async () => {
  const R = await vi.importActual<typeof import('react')>('react');
  return {
    AdaptiveWrapper: ({ children }: any) => R.createElement(R.Fragment, null, children),
  };
});

// Mock AdaptiveScaffolding
vi.mock('./AdaptiveScaffolding', () => ({
  ScaffoldingLevel: { Beginner: 'beginner', Intermediate: 'intermediate', Expert: 'expert' },
}));

import IntentCanvas from './IntentCanvas';
import * as geminiService from '../services/geminiService';
import { IVCUStatus, ModelTier } from '../types';

// Mock high-latency services
vi.mock('../services/geminiService', () => ({
  parseIntent: vi.fn(),
  generateVerifiedCode: vi.fn(),
  generateIntentVisual: vi.fn(),
  getEstimatedCost: vi.fn().mockResolvedValue({ estimated_cost_usd: 0.01, input_tokens: 100, output_tokens: 200 }),
  snapshotState: vi.fn().mockResolvedValue(true),
}));

describe('IntentCanvas Component Strategy', () => {
  const mockOnGenerated = vi.fn();
  const mockAddLog = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('PROBE: Undo/Redo Semantic Stack Integrity', async () => {
    render(<IntentCanvas onGenerated={mockOnGenerated} addLog={mockAddLog} />);
    const textarea = screen.getAllByPlaceholderText(/Articulate your architectural intent.../i)[0] as HTMLTextAreaElement;

    // Stage 1: Initial Intent
    fireEvent.change(textarea, { target: { value: 'State Alpha' } });
    act(() => { vi.advanceTimersByTime(1000); });

    // Stage 2: Modified Intent
    fireEvent.change(textarea, { target: { value: 'State Beta' } });
    act(() => { vi.advanceTimersByTime(1000); });

    // Probe Undo
    const undoBtn = screen.getByLabelText(/Undo semantic change/i);
    fireEvent.click(undoBtn);
    expect(textarea.value).toBe('State Alpha');

    // Probe Redo
    const redoBtn = screen.getByLabelText(/Redo semantic change/i);
    fireEvent.click(redoBtn);
    expect(textarea.value).toBe('State Beta');
  });

  it('PROBE: Model Tier Cost Assignment', async () => {
    vi.useRealTimers();
    render(<IntentCanvas onGenerated={mockOnGenerated} addLog={mockAddLog} />);

    // Select Frontier Tier
    const frontierBtn = screen.getByText('Frontier');
    fireEvent.click(frontierBtn);

    // Set valid intent to enable button
    const textarea = screen.getAllByPlaceholderText(/Articulate your architectural intent.../i)[0] as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'System architecture planning intent' } });

    // Mock successful synthesis
    (geminiService.parseIntent as any).mockResolvedValue({ confidence: 1, constraints: [] });
    (geminiService.generateVerifiedCode as any).mockResolvedValue('// Code');

    const submitBtn = screen.getByText('EXECUTE_INTENT');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      const calls = mockOnGenerated.mock.calls;
      const finalCall = calls[calls.length - 1][0];
      expect(finalCall.cost).toBe(0.125);
    }, { timeout: 5000 });
  });

  it('PROBE: Async Orchestration Pipeline', async () => {
    vi.useRealTimers();
    render(<IntentCanvas onGenerated={mockOnGenerated} addLog={mockAddLog} />);
    const textarea = screen.getAllByPlaceholderText(/Articulate your architectural intent.../i)[0] as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Secure Auth' } });

    // Setup partial success
    (geminiService.parseIntent as any).mockResolvedValue({
      confidence: 0.9,
      constraints: ['Use Argon2']
    });
    (geminiService.generateVerifiedCode as any).mockResolvedValue('const auth = () => {}');

    const submitBtn = screen.getByText('EXECUTE_INTENT');
    fireEvent.click(submitBtn);

    // Verify initial "Generating" signal
    expect(mockOnGenerated).toHaveBeenCalledWith(expect.objectContaining({
      status: IVCUStatus.Generating
    }));

    await waitFor(() => {
      expect(mockOnGenerated).toHaveBeenLastCalledWith(expect.objectContaining({
        status: IVCUStatus.Verified,
        code: 'const auth = () => {}'
      }));
    }, { timeout: 5000 });

    expect(mockAddLog).toHaveBeenCalledWith(expect.stringContaining('Synthesis finalized successfully'));
  });
});
