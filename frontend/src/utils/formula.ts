
// Canonical format: node("nodeId")
const CANONICAL_NODE_REGEX = /node\("([^"]+)"\)/g;

// Display format: snake_cased_name
// We use a regex that captures potential identifiers
// Note: This is a simple tokenizer-like regex. It might match substrings in some complex cases,
// but for this MVP it serves the purpose of finding words.
// A more robust approach would use a real tokenizer.
const IDENTIFIER_REGEX = /[a-zA-Z_][a-zA-Z0-9_]*/g;

/**
 * Converts a display formula (using snake_cased names) to a canonical formula (using stored Node IDs).
 * 
 * Example:
 * Display: "base_salary * 2"
 * Canonical: "node("salary_node_id") * 2"
 * 
 * @param displayFormula The formula string as typed by the user
 * @param varNameToId Map of snake_cased identifier -> Node ID
 * @returns Canonical formula string
 */
export function toCanonical(
    displayFormula: string,
    varNameToId: Record<string, string>
): string {
    if (!displayFormula) return '';

    // We simply replace known variable names with their specific canonical ID form
    // We sort keys by length descending to prevent partial replacements (e.g. replacing 'rate' in 'tax_rate')
    // This is a naive but effective strategy for simple formula replacements

    // Actually, a better approach is to use a replacer function on identifier tokens
    return displayFormula.replace(IDENTIFIER_REGEX, (match) => {
        const nodeId = varNameToId[match];
        if (nodeId) {
            return `node("${nodeId}")`;
        }
        // If not a known variable, return as is (could be a function name like 'sum' or 'max')
        return match;
    });
}

/**
 * Converts a canonical formula (containing Node IDs) to a display-friendly formula.
 * 
 * Example:
 * Canonical: "node("salary_node_id") * 2"
 * Display: "base_salary * 2"
 * 
 * @param canonicalFormula The stored formula string
 * @param idToVarName Map of Node ID -> value to display (usually snake_cased var_name)
 * @returns Display formula string
 */
export function toDisplay(
    canonicalFormula: string,
    idToVarName: Record<string, string>
): string {
    if (!canonicalFormula) return '';

    return canonicalFormula.replace(CANONICAL_NODE_REGEX, (_, nodeId) => {
        const varName = idToVarName[nodeId];
        // If we have a name, use it. If not (deleted node?), keep the raw ID or some fallback
        return varName || nodeId; // Fallback to ID if name not found (unlikely but possible)
    });
}

/**
 * Extracts referenced Node IDs from a canonical formula.
 */
export function extractReferencedIds(canonicalFormula: string): string[] {
    if (!canonicalFormula) return [];

    const matches = [...canonicalFormula.matchAll(CANONICAL_NODE_REGEX)];
    return matches.map(m => m[1]);
}
