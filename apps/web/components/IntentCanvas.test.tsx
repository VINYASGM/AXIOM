
/**
 * @axiom-test-suite IntentCanvas.v2
 * Logic Probes: Undo/Redo, Async Orchestration, Tier Validation
 */

import React from 'react';
import { render, screen, fireEvent, act, cleanup, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import IntentCanvas from './IntentCanvas';
import * as geminiService from '../services/geminiService';
import { IVCUStatus, ModelTier } from '../types';

// Mock high-latency services
vi.mock('../services/geminiService', () => ({
  parseIntent: vi.fn(),
  generateVerifiedCode: vi.fn(),
  generateIntentVisual: vi.fn(),
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

    // expect(lastCall.cost).toBe(0.125); // Wait for verification
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
