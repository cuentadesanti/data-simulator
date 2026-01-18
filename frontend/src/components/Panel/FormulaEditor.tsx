import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { getEffectiveVarName } from '../../types/dag';

interface FormulaEditorProps {
  nodeId: string;
}

interface ValidationError {
  message: string;
  type: 'syntax' | 'reference' | 'warning';
}

const AVAILABLE_FUNCTIONS = [
  { name: 'abs', description: 'Absolute value', example: 'abs(x)' },
  { name: 'min', description: 'Minimum of values', example: 'min(x, y)' },
  { name: 'max', description: 'Maximum of values', example: 'max(x, y)' },
  { name: 'sqrt', description: 'Square root', example: 'sqrt(x)' },
  { name: 'pow', description: 'Power', example: 'pow(x, 2)' },
  { name: 'exp', description: 'Exponential', example: 'exp(x)' },
  { name: 'log', description: 'Natural logarithm', example: 'log(x)' },
  { name: 'log10', description: 'Log base 10', example: 'log10(x)' },
  { name: 'sin', description: 'Sine', example: 'sin(x)' },
  { name: 'cos', description: 'Cosine', example: 'cos(x)' },
  { name: 'tan', description: 'Tangent', example: 'tan(x)' },
  { name: 'round', description: 'Round to nearest integer', example: 'round(x)' },
  { name: 'floor', description: 'Round down', example: 'floor(x)' },
  { name: 'ceil', description: 'Round up', example: 'ceil(x)' },
  { name: 'clamp', description: 'Clamp between min and max', example: 'clamp(x, 0, 100)' },
  {
    name: 'if_else',
    description: 'Conditional: if_else(cond, then, else)',
    example: 'if_else(x > 0, x, 0)',
  },
];

interface Suggestion {
  type: 'node' | 'function' | 'constant';
  id: string;
  name: string;
  description: string;
  insertText: string;
  matchScore: number; // Higher = better match
}

export const FormulaEditor: React.FC<FormulaEditorProps> = ({ nodeId }) => {
  const updateNode = useDAGStore((state) => state.updateNode);
  const nodes = useDAGStore((state) => state.nodes);
  const edges = useDAGStore((state) => state.edges);
  const context = useDAGStore((state) => state.context);

  // Read formula directly from store
  const formula = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.config.formula || '';
  });

  const [showHelp, setShowHelp] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [isValid, setIsValid] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Get direct parents (nodes with edges pointing TO this node)
  const parentIds = useMemo(
    () => new Set(edges.filter((e) => e.target === nodeId).map((e) => e.source)),
    [edges, nodeId]
  );

  // Get available variables (only direct parents from edges) with their var_names
  const availableVariables = useMemo(
    () =>
      nodes
        .filter((n) => parentIds.has(n.id))
        .map((n) => ({
          ...n.data.config,
          varName: getEffectiveVarName(n.data.config),
        })),
    [nodes, parentIds]
  );

  // Get context keys
  const contextKeys = useMemo(() => Object.keys(context), [context]);

  // Build available variable set for validation (using var_names, not node IDs)
  const availableVarSet = useMemo(
    () =>
      new Set([
        ...availableVariables.map((v) => v.varName), // Use var_names
        ...contextKeys,
        'PI',
        'E',
        'TRUE',
        'FALSE', // Reserved constants
      ]),
    [availableVariables, contextKeys]
  );

  // Reserved functions for validation
  const reservedFunctions = useMemo(
    () =>
      new Set([
        'abs',
        'min',
        'max',
        'round',
        'floor',
        'ceil',
        'sqrt',
        'log',
        'log10',
        'exp',
        'pow',
        'sin',
        'cos',
        'tan',
        'clamp',
        'if_else',
        'and',
        'or',
        'not',
        'if',
        'else',
        'in',
        'is',
      ]),
    []
  );

  // Validate formula syntax
  const validateFormula = useCallback(
    (formulaText: string): ValidationError[] => {
      const errors: ValidationError[] = [];

      // Empty formula is an error for deterministic nodes
      if (!formulaText.trim()) {
        errors.push({ message: 'Formula is required for deterministic nodes', type: 'syntax' });
        return errors;
      }

      // Check for basic syntax errors
      // 1. Mismatched parentheses
      let parenCount = 0;
      let braceCount = 0;
      let bracketCount = 0;
      for (const char of formulaText) {
        if (char === '(') parenCount++;
        if (char === ')') parenCount--;
        if (char === '{') braceCount++;
        if (char === '}') braceCount--;
        if (char === '[') bracketCount++;
        if (char === ']') bracketCount--;

        if (parenCount < 0 || braceCount < 0 || bracketCount < 0) {
          errors.push({ message: 'Mismatched brackets or parentheses', type: 'syntax' });
          break;
        }
      }

      if (parenCount > 0) {
        errors.push({ message: 'Unclosed opening parenthesis', type: 'syntax' });
      } else if (parenCount < 0) {
        errors.push({ message: 'Extra closing parenthesis', type: 'syntax' });
      }

      if (bracketCount > 0) {
        errors.push({ message: 'Unclosed opening bracket', type: 'syntax' });
      } else if (bracketCount < 0) {
        errors.push({ message: 'Extra closing bracket', type: 'syntax' });
      }

      // 2. Check for trailing operators
      const trailingOperatorRegex = /[+\-*/%]$/;
      if (trailingOperatorRegex.test(formulaText.trim())) {
        errors.push({ message: 'Formula ends with an operator', type: 'syntax' });
      }

      // 3. Check for leading operators (except unary minus/plus)
      const leadingOperatorRegex = /^[*/%]/;
      if (leadingOperatorRegex.test(formulaText.trim())) {
        errors.push({ message: 'Formula starts with an invalid operator', type: 'syntax' });
      }

      // 4. Check for double operators (excluding **)
      const doubleOperatorRegex = /[+\-*/%]{2,}/;
      const formulaWithoutPow = formulaText.replace(/\*\*/g, '@@');
      if (doubleOperatorRegex.test(formulaWithoutPow)) {
        errors.push({ message: 'Consecutive operators found', type: 'syntax' });
      }

      // 5. Check for empty parentheses
      if (/\(\s*\)/.test(formulaText)) {
        errors.push({ message: 'Empty parentheses found', type: 'syntax' });
      }

      // 6. Check for invalid variable references
      const variablePattern = /\b([a-z_][a-z0-9_]*)\b(?!\s*\()/gi;
      const matches = formulaText.matchAll(variablePattern);

      const invalidVars = new Set<string>();
      for (const match of matches) {
        const varName = match[1];
        if (!availableVarSet.has(varName) && !reservedFunctions.has(varName.toLowerCase())) {
          invalidVars.add(varName);
        }
      }

      if (invalidVars.size > 0) {
        const varList = Array.from(invalidVars).join(', ');
        errors.push({
          message: `Unknown variable(s): ${varList}. Add edges from these nodes or check spelling.`,
          type: 'reference',
        });
      }

      return errors;
    },
    [availableVarSet, reservedFunctions]
  );

  // Validate formula on change
  useEffect(() => {
    console.log('[FormulaEditor] Validating formula:', formula);
    const errors = validateFormula(formula);
    console.log('[FormulaEditor] Validation result:', { errors, isValid: errors.length === 0 });
    setValidationErrors(errors);
    setIsValid(errors.length === 0 && formula.trim().length > 0);
  }, [formula, validateFormula]);

  // Build all suggestions
  const allSuggestions = useMemo(
    () => [
      // Parent nodes (from edges) - use varName for id and insertText
      ...availableVariables.map((node) => ({
        type: 'node' as const,
        id: node.varName, // Use varName for matching
        name: node.name,
        description: `${node.kind} • ${node.dtype || 'unknown'} • ${node.scope}`,
        insertText: node.varName, // Insert varName, not node ID
        matchScore: 0,
      })),
      // Context keys
      ...contextKeys.map((key) => ({
        type: 'node' as const,
        id: key,
        name: key,
        description: 'context value',
        insertText: key,
        matchScore: 0,
      })),
      // Built-in constants
      {
        type: 'constant' as const,
        id: 'PI',
        name: 'PI',
        description: '3.14159...',
        insertText: 'PI',
        matchScore: 0,
      },
      {
        type: 'constant' as const,
        id: 'E',
        name: 'E',
        description: '2.71828...',
        insertText: 'E',
        matchScore: 0,
      },
      {
        type: 'constant' as const,
        id: 'TRUE',
        name: 'TRUE',
        description: 'Boolean true',
        insertText: 'TRUE',
        matchScore: 0,
      },
      {
        type: 'constant' as const,
        id: 'FALSE',
        name: 'FALSE',
        description: 'Boolean false',
        insertText: 'FALSE',
        matchScore: 0,
      },
      // Functions
      ...AVAILABLE_FUNCTIONS.map((func) => ({
        type: 'function' as const,
        id: func.name,
        name: func.name,
        description: func.description,
        insertText: func.name + '(',
        matchScore: 0,
      })),
    ],
    [availableVariables, contextKeys]
  );

  // Get the current word being typed at cursor position
  const getCurrentWord = useCallback((text: string, position: number) => {
    const beforeCursor = text.slice(0, position);
    const match = beforeCursor.match(/[a-zA-Z_][a-zA-Z0-9_]*$/);
    return match ? match[0] : '';
  }, []);

  // Score and filter suggestions based on current word
  const updateSuggestions = useCallback(
    (text: string, position: number) => {
      const currentWord = getCurrentWord(text, position).toLowerCase();
      if (currentWord.length === 0) {
        setShowSuggestions(false);
        return;
      }

      // Score each suggestion based on match quality
      const scored = allSuggestions
        .map((s) => {
          const idLower = s.id.toLowerCase();
          let score = 0;

          if (idLower === currentWord) {
            // Exact match - highest score
            score = 100;
          } else if (idLower.startsWith(currentWord)) {
            // Prefix match - high score
            score = 80 + (currentWord.length / idLower.length) * 20;
          } else if (idLower.includes(currentWord)) {
            // Contains match - medium score
            score = 40 + (currentWord.length / idLower.length) * 20;
          } else {
            // Check for fuzzy match (all chars in order)
            let matchIdx = 0;
            for (const char of idLower) {
              if (matchIdx < currentWord.length && char === currentWord[matchIdx]) {
                matchIdx++;
              }
            }
            if (matchIdx === currentWord.length) {
              score = 20 + (currentWord.length / idLower.length) * 10;
            }
          }

          return { ...s, matchScore: score };
        })
        .filter((s) => s.matchScore > 0);

      // Sort by score (descending), then by type (nodes first), then alphabetically
      const sorted = scored.sort((a, b) => {
        if (b.matchScore !== a.matchScore) return b.matchScore - a.matchScore;
        if (a.type !== b.type) {
          const typeOrder = { node: 0, constant: 1, function: 2 };
          return typeOrder[a.type] - typeOrder[b.type];
        }
        return a.id.localeCompare(b.id);
      });

      if (sorted.length > 0) {
        setSuggestions(sorted.slice(0, 10)); // Limit to 10 suggestions
        setSelectedIndex(0);
        setShowSuggestions(true);
      } else {
        setShowSuggestions(false);
      }
    },
    [allSuggestions, getCurrentWord]
  );

  // Insert suggestion at cursor position
  const insertSuggestion = useCallback(
    (suggestion: Suggestion) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const currentWord = getCurrentWord(formula, cursorPosition);
      const beforeWord = formula.slice(0, cursorPosition - currentWord.length);
      const afterCursor = formula.slice(cursorPosition);

      const newFormula = beforeWord + suggestion.insertText + afterCursor;
      updateNode(nodeId, { formula: newFormula });

      // Move cursor to end of inserted text
      const newPosition = beforeWord.length + suggestion.insertText.length;
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(newPosition, newPosition);
      }, 0);

      setShowSuggestions(false);
    },
    [formula, cursorPosition, getCurrentWord, nodeId, updateNode]
  );

  const handleFormulaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newFormula = e.target.value;
    const newPosition = e.target.selectionStart || 0;
    console.log('[FormulaEditor] handleFormulaChange:', { newFormula, nodeId });
    setCursorPosition(newPosition);
    updateNode(nodeId, { formula: newFormula });
    updateSuggestions(newFormula, newPosition);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
      case 'Tab':
        if (suggestions[selectedIndex]) {
          e.preventDefault();
          insertSuggestion(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        break;
    }
  };

  const handleSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement;
    const pos = target.selectionStart || 0;
    setCursorPosition(pos);
    updateSuggestions(formula, pos);
  };

  // Scroll selected suggestion into view
  useEffect(() => {
    if (suggestionsRef.current && showSuggestions) {
      const selectedElement = suggestionsRef.current.children[selectedIndex] as HTMLElement;
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex, showSuggestions]);

  const insertText = (text: string) => {
    const textarea = textareaRef.current;
    const newFormula = formula + text;
    updateNode(nodeId, { formula: newFormula });
    setTimeout(() => {
      if (textarea) {
        textarea.focus();
        textarea.setSelectionRange(newFormula.length, newFormula.length);
      }
    }, 0);
  };

  // Highlight matched characters in suggestion
  const highlightMatch = (text: string, query: string) => {
    if (!query) return <span>{text}</span>;

    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();

    // Try prefix match first
    if (lowerText.startsWith(lowerQuery)) {
      return (
        <>
          <span className="font-bold text-blue-600">{text.slice(0, query.length)}</span>
          <span>{text.slice(query.length)}</span>
        </>
      );
    }

    // Try contains match
    const idx = lowerText.indexOf(lowerQuery);
    if (idx >= 0) {
      return (
        <>
          <span>{text.slice(0, idx)}</span>
          <span className="font-bold text-blue-600">{text.slice(idx, idx + query.length)}</span>
          <span>{text.slice(idx + query.length)}</span>
        </>
      );
    }

    return <span>{text}</span>;
  };

  const currentWord = getCurrentWord(formula, cursorPosition);

  return (
    <div className="space-y-4">
      <div className="border-b border-gray-200 pb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
            Formula Editor
          </h3>
          {/* Live validation status */}
          {formula.trim() && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}
            >
              {isValid ? (
                <>
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Valid
                </>
              ) : (
                <>
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Invalid
                </>
              )}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setShowHelp(!showHelp)}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          {showHelp ? 'Hide Help' : 'Show Help'}
        </button>
      </div>

      {/* Formula Input */}
      <div className="relative">
        <label htmlFor="formula" className="block text-sm font-medium text-gray-700 mb-1">
          Formula Expression
        </label>
        <textarea
          ref={textareaRef}
          id="formula"
          value={formula}
          onChange={handleFormulaChange}
          onKeyDown={handleKeyDown}
          onSelect={handleSelect}
          onClick={handleSelect}
          rows={4}
          placeholder="e.g., parent_node * 2 + sqrt(other_node)"
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:ring-2 text-sm font-mono ${
            validationErrors.length > 0
              ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
              : isValid
                ? 'border-green-300 focus:ring-green-500 focus:border-green-500'
                : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
          }`}
        />

        {/* Validation Status Messages */}
        {validationErrors.length > 0 ? (
          <div className="mt-2 space-y-1">
            {validationErrors.map((error, index) => (
              <div
                key={index}
                className={`flex items-start gap-2 text-xs px-2 py-1.5 rounded ${
                  error.type === 'syntax'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : error.type === 'reference'
                      ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                      : 'bg-blue-50 text-blue-700 border border-blue-200'
                }`}
              >
                <span className="flex-shrink-0">
                  {error.type === 'syntax' ? '⚠️' : error.type === 'reference' ? '🔗' : 'ℹ️'}
                </span>
                <span>{error.message}</span>
              </div>
            ))}
          </div>
        ) : isValid ? (
          <div className="mt-2 flex items-center gap-2 text-xs px-2 py-1.5 rounded bg-green-50 text-green-700 border border-green-200">
            <span>✓</span>
            <span>Formula syntax is valid</span>
          </div>
        ) : null}

        {/* Autocomplete Suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div
            ref={suggestionsRef}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-64 overflow-y-auto"
          >
            <div className="px-3 py-1.5 bg-gray-50 border-b border-gray-200 text-xs text-gray-500">
              {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''} • ↑↓ navigate •
              Tab/Enter select
            </div>
            {suggestions.map((suggestion, index) => (
              <button
                key={suggestion.id + suggestion.type}
                type="button"
                onClick={() => insertSuggestion(suggestion)}
                className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-blue-50 ${
                  index === selectedIndex ? 'bg-blue-100' : ''
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                      suggestion.type === 'node'
                        ? 'bg-blue-100 text-blue-700'
                        : suggestion.type === 'constant'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-purple-100 text-purple-700'
                    }`}
                  >
                    {suggestion.type === 'node'
                      ? 'var'
                      : suggestion.type === 'constant'
                        ? 'const'
                        : 'fn'}
                  </span>
                  <span className="font-mono text-sm text-gray-900">
                    {highlightMatch(suggestion.id, currentWord)}
                  </span>
                </div>
                <span className="text-xs text-gray-500 truncate ml-2 max-w-[150px]">
                  {suggestion.description}
                </span>
              </button>
            ))}
          </div>
        )}

        <p className="mt-1 text-xs text-gray-500">
          Type to see autocomplete suggestions. Use ↑↓ to navigate, Tab/Enter to select, Esc to
          close.
        </p>
      </div>

      {/* Available Variables Quick Reference */}
      {availableVariables.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-700">Quick Insert</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {availableVariables.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => insertText(node.varName)}
                className="px-2 py-1 text-xs font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                title={`${node.name} (${node.dtype || 'unknown'})`}
              >
                {node.varName}
              </button>
            ))}
            {contextKeys.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => insertText(key)}
                className="px-2 py-1 text-xs font-mono bg-purple-50 text-purple-700 border border-purple-200 rounded hover:bg-purple-100 transition-colors"
                title="Context variable"
              >
                {key}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* No Variables Warning */}
      {availableVariables.length === 0 && contextKeys.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 text-sm text-yellow-800">
          <p className="font-medium">No variables available</p>
          <p className="mt-1 text-xs">
            Draw edges from other nodes to this node to use them in your formula.
          </p>
        </div>
      )}

      {/* Help Panel */}
      {showHelp && (
        <div className="space-y-3 pt-2 border-t border-gray-200">
          {/* Available Functions */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Available Functions</h4>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-2 max-h-48 overflow-y-auto">
              <div className="grid grid-cols-2 gap-1">
                {AVAILABLE_FUNCTIONS.map((func) => (
                  <button
                    key={func.name}
                    type="button"
                    onClick={() => insertText(func.example)}
                    className="text-left px-2 py-1 bg-white border border-gray-200 rounded hover:bg-blue-50 hover:border-blue-300 transition-colors"
                  >
                    <div className="text-xs font-mono text-gray-900">{func.name}()</div>
                    <div className="text-xs text-gray-500 truncate">{func.description}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Operators */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Operators</h4>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="font-mono text-blue-600">+</span> Add
                </div>
                <div>
                  <span className="font-mono text-blue-600">-</span> Subtract
                </div>
                <div>
                  <span className="font-mono text-blue-600">*</span> Multiply
                </div>
                <div>
                  <span className="font-mono text-blue-600">/</span> Divide
                </div>
                <div>
                  <span className="font-mono text-blue-600">**</span> Power
                </div>
                <div>
                  <span className="font-mono text-blue-600">%</span> Modulo
                </div>
                <div>
                  <span className="font-mono text-blue-600">&gt;</span> Greater
                </div>
                <div>
                  <span className="font-mono text-blue-600">&lt;</span> Less
                </div>
                <div>
                  <span className="font-mono text-blue-600">==</span> Equal
                </div>
              </div>
            </div>
          </div>

          {/* Examples */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Examples</h4>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-2 space-y-1 text-xs">
              <code className="block bg-white px-2 py-1 rounded border border-gray-200 text-blue-600">
                x * 2 + y
              </code>
              <code className="block bg-white px-2 py-1 rounded border border-gray-200 text-blue-600">
                sqrt(abs(x)) + max(y, 0)
              </code>
              <code className="block bg-white px-2 py-1 rounded border border-gray-200 text-blue-600">
                if_else(x &gt; 0, x, 0)
              </code>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
