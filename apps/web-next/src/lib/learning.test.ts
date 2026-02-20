// Minimal test runner shim since we can't easily install vitest in this environment
function describe(name: string, fn: () => void) { console.log(`\n${name}`); fn(); }
function test(name: string, fn: () => void) {
    try { fn(); console.log(`✓ ${name}`); }
    catch (e) { console.error(`✗ ${name}`, e); }
}
function expect(actual: any) {
    return {
        toBe(expected: any) {
            if (actual !== expected) throw new Error(`Expected ${expected}, got ${actual}`);
        }
    }
}

import { detectArchitecturalComplexity, LearningEvent } from './learning';

describe('detectArchitecturalComplexity', () => {
    test('should return BASIC_INTENT for empty or simple intent', () => {
        expect(detectArchitecturalComplexity(null)).toBe('BASIC_INTENT');
        expect(detectArchitecturalComplexity({})).toBe('BASIC_INTENT');
        expect(detectArchitecturalComplexity({ text: 'Simple hello' })).toBe('BASIC_INTENT');
    });

    test('should detect MULTI_STEP_FLOW', () => {
        const intent = { steps: [1, 2, 3, 4] };
        expect(detectArchitecturalComplexity(intent)).toBe('MULTI_STEP_FLOW');
    });

    test('should detect STATEFUL_LOGIC', () => {
        const intent = { hasState: true };
        expect(detectArchitecturalComplexity(intent)).toBe('STATEFUL_LOGIC');
    });

    test('should detect ARCHITECTURAL_COMPOSITION', () => {
        const intent = {
            components: [1, 2, 3, 4],
            hasState: true
        };
        expect(detectArchitecturalComplexity(intent)).toBe('ARCHITECTURAL_COMPOSITION');

        const intent2 = {
            components: [1, 2, 3, 4],
            hasAPIs: true // mocking heuristic check
        };
        expect(detectArchitecturalComplexity(intent2)).toBe('ARCHITECTURAL_COMPOSITION');
    });

    test('should detect HIGH_COMPLEXITY_SYSTEM', () => {
        const intent = {
            components: [1, 2, 3, 4, 5, 6],
            hasState: true,
            hasAPIs: true,
            usesEventBus: true
        };
        expect(detectArchitecturalComplexity(intent)).toBe('HIGH_COMPLEXITY_SYSTEM');
    });
});
