import { describe, it, expect } from 'vitest';
import { toCanonical, toDisplay, extractReferencedIds } from './formula';

describe('Formula Utils', () => {
    describe('toCanonical', () => {
        it('converts basic varNames to node IDs', () => {
            const varMap = {
                'salary': 'node-1',
                'tax': 'node-2'
            };

            expect(toCanonical('salary * 2', varMap)).toBe('node("node-1") * 2');
            expect(toCanonical('salary + tax', varMap)).toBe('node("node-1") + node("node-2")');
        });

        it('ignores unknown identifiers (assumed to be functions or constants)', () => {
            const varMap = { 'x': '1' };
            expect(toCanonical('max(x, 100)', varMap)).toBe('max(node("1"), 100)');
            expect(toCanonical('custom_func(x)', varMap)).toBe('custom_func(node("1"))');
        });


        it('handles substrings correctly if using regex word boundaries', () => {
            // NOTE: Our current IDENTIFIER_REGEX matches substrings. 
            // If we want strict full-word replacement we need \b boundaries or a lexer.
            // For now, let's verify exact behavior.
            // If we map 'rate' -> 'id1' and 'tax_rate' -> 'id2'
            // 'tax_rate' contains 'rate'.
            // If we blindly replace 'rate', 'tax_rate' becomes 'tax_node("id1")'.
            // The current implementation uses `replace(IDENTIFIER_REGEX, ...)` which tokenizes by word.
            // So 'tax_rate' is ONE token, and 'rate' is another.

            const varMap = {
                'rate': 'id-1',
                'tax_rate': 'id-2'
            };

            // 'tax_rate' should be replaced by id-2, NOT 'tax_' + id-1
            expect(toCanonical('tax_rate', varMap)).toBe('node("id-2")');
            expect(toCanonical('rate', varMap)).toBe('node("id-1")');
            expect(toCanonical('tax_rate + rate', varMap)).toBe('node("id-2") + node("id-1")');
        });

        it('handles overlapping names (prefix problem)', () => {
            const varMap = {
                'a': 'id-1',
                'aa': 'id-2'
            };
            expect(toCanonical('aa + a', varMap)).toBe('node("id-2") + node("id-1")');
        });

        it('ignores numeric literals', () => {
            const varMap = { 'x': 'id-1' };
            expect(toCanonical('x + 100', varMap)).toBe('node("id-1") + 100');
            expect(toCanonical('x + 100.50', varMap)).toBe('node("id-1") + 100.50');
        });

        it('ignores python keywords (simulated as unknown vars)', () => {
            // Assuming 'if' isn't in varMap
            const varMap = { 'x': 'id-1' };
            expect(toCanonical('if x > 0', varMap)).toBe('if node("id-1") > 0');
        });

        it('handles empty input', () => {
            expect(toCanonical('', {})).toBe('');
            // @ts-ignore
            expect(toCanonical(null, {})).toBe('');
            // @ts-ignore
            expect(toCanonical(undefined, {})).toBe('');
        });
    });

    describe('toDisplay', () => {
        it('converts node IDs back to varNames', () => {
            const idMap = {
                'node-1': 'salary',
                'node-2': 'tax'
            };

            expect(toDisplay('node("node-1") * 2', idMap)).toBe('salary * 2');
        });

        it('handles multiple occurrences', () => {
            const idMap = { 'node-1': 'x' };
            expect(toDisplay('node("node-1") + node("node-1")', idMap)).toBe('x + x');
        });

        it('preserves formatting', () => {
            const idMap = { 'node-1': 'x' };
            expect(toDisplay('  node("node-1")  *  2  ', idMap)).toBe('  x  *  2  ');
        });
    });

    describe('extractReferencedIds', () => {
        it('finds all node IDs', () => {
            const formula = 'node("a") + node("b") * node("a")';
            expect(extractReferencedIds(formula)).toEqual(['a', 'b', 'a']);
        });
    });
});
