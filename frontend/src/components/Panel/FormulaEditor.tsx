import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { getEffectiveVarName } from '../../types/dag';
import { toCanonical, toDisplay } from '../../utils/formula';
import { InputChips } from './InputChips';

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

  // Read formula directly from store (Canonical Form)
  const canonicalFormula = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.config.formula || '';
  });

  // Local state for display
  const [displayFormula, setDisplayFormula] = useState('');
  const [showHelp, setShowHelp] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [isValid, setIsValid] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const isEditingRef = useRef(false);

  // Mappings for conversion
  const idToVarName = useMemo(() => {
    const map: Record<string, string> = {};
    nodes.forEach((n) => {
      map[n.id] = getEffectiveVarName(n.data.config);
    });
    return map;
  }, [nodes]);

  const varNameToId = useMemo(() => {
    const map: Record<string, string> = {};
    nodes.forEach((n) => {
      const varName = getEffectiveVarName(n.data.config);
      map[varName] = n.id;
    });
    return map;
  }, [nodes]);

  // Sync display formula when canonical formula changes externally (or on mount/node switch)
  // Reset editing state and update display from canonical
  useEffect(() => {
    isEditingRef.current = false;
    setDisplayFormula(toDisplay(canonicalFormula, idToVarName));
  }, [canonicalFormula, nodeId, idToVarName]);

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

  // Validate formula syntax (operates on DISPLAY formula)
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
    const errors = validateFormula(displayFormula);
    setValidationErrors(errors);
    setIsValid(errors.length === 0 && displayFormula.trim().length > 0);
  }, [displayFormula, validateFormula]);

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

      const currentWord = getCurrentWord(displayFormula, cursorPosition);
      const beforeWord = displayFormula.slice(0, cursorPosition - currentWord.length);
      const afterCursor = displayFormula.slice(cursorPosition);

      const newFormula = beforeWord + suggestion.insertText + afterCursor;

      // Update display AND canonical
      setDisplayFormula(newFormula);
      const newCanonical = toCanonical(newFormula, varNameToId);
      updateNode(nodeId, { formula: newCanonical });

      // Move cursor to end of inserted text
      const newPosition = beforeWord.length + suggestion.insertText.length;
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(newPosition, newPosition);
      }, 0);

      setShowSuggestions(false);
    },
    [displayFormula, cursorPosition, getCurrentWord, nodeId, updateNode, varNameToId]
  );

  const handleFormulaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newFormula = e.target.value;
    const newPosition = e.target.selectionStart || 0;

    // Mark as actively editing to prevent sync from overwriting
    isEditingRef.current = true;

    setCursorPosition(newPosition);
    setDisplayFormula(newFormula);

    // Convert to canonical and update store
    const newCanonical = toCanonical(newFormula, varNameToId);
    updateNode(nodeId, { formula: newCanonical });

    updateSuggestions(newFormula, newPosition);
  };

  const handleFocus = () => {
    isEditingRef.current = true;
  };

  const handleBlur = () => {
    isEditingRef.current = false;
    // Sync display from canonical on blur to ensure consistency
    setDisplayFormula(toDisplay(canonicalFormula, idToVarName));
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
    updateSuggestions(displayFormula, pos);
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
    const newFormula = displayFormula + text;

    setDisplayFormula(newFormula);
    const newCanonical = toCanonical(newFormula, varNameToId);
    updateNode(nodeId, { formula: newCanonical });

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

  const currentWord = getCurrentWord(displayFormula, cursorPosition);

  // Build a contextual placeholder using actual parent var names
  const placeholder = useMemo(() => {
    if (availableVariables.length >= 2) {
      const [a, b] = availableVariables;
      return `e.g., ${a.varName} * 2 + ${b.varName}`;
    }
    if (availableVariables.length === 1) {
      return `e.g., ${availableVariables[0].varName} * 2 + 1`;
    }
    return 'e.g., x * 2 + sqrt(y)';
  }, [availableVariables]);

  return (
    <div className="space-y-3">
      {/* Label row: "Formula" + validation indicator + info hover + help toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <label htmlFor="formula" className="text-xs font-medium text-gray-500">
            Formula
          </label>
          {displayFormula.trim() && (
            <span
              className={`text-xs px-1.5 py-0.5 rounded ${
                isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}
            >
              {isValid ? '✓' : '!'}
            </span>
          )}
          <button
            type="button"
            onClick={() => setShowInfo(!showInfo)}
            className="text-xs text-gray-400 hover:text-blue-600 leading-none"
          >
            ?
          </button>
        </div>
        <button
          type="button"
          onClick={() => setShowHelp(!showHelp)}
          className="text-xs text-gray-400 hover:text-blue-600"
        >
          {showHelp ? 'hide help' : 'help'}
        </button>
      </div>

      {/* Info panel */}
      {showInfo && (
        <div className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-2.5 py-2 space-y-1">
          <p>Write a math expression using connected parent node variables, operators (<code className="text-blue-600">+ - * / **</code>), and functions (<code className="text-blue-600">sqrt, abs, log, clamp, if_else</code>).</p>
          <p>Start typing to see autocomplete suggestions. Click a chip below the input to insert a variable name.</p>
        </div>
      )}

      {/* Textarea */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          id="formula"
          value={displayFormula}
          onChange={handleFormulaChange}
          onKeyDown={handleKeyDown}
          onSelect={handleSelect}
          onClick={handleSelect}
          onFocus={handleFocus}
          onBlur={handleBlur}
          rows={2}
          placeholder={placeholder}
          className={`w-full px-2 py-1.5 border rounded-md text-sm font-mono focus:ring-1 ${
            validationErrors.length > 0
              ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
              : isValid
                ? 'border-green-300 focus:ring-green-500 focus:border-green-500'
                : 'border-gray-200 focus:ring-blue-500 focus:border-blue-500'
          }`}
        />

        {/* Validation errors — compact, only shown when there are errors */}
        {validationErrors.length > 0 && (
          <div className="mt-1 space-y-0.5">
            {validationErrors.map((error, index) => (
              <div key={index} className="text-xs text-red-600">
                {error.message}
              </div>
            ))}
          </div>
        )}

        {/* Autocomplete Suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div
            ref={suggestionsRef}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto"
          >
            {suggestions.map((suggestion, index) => (
              <button
                key={suggestion.id + suggestion.type}
                type="button"
                onClick={() => insertSuggestion(suggestion)}
                className={`w-full text-left px-2.5 py-1.5 flex items-center justify-between hover:bg-blue-50 ${
                  index === selectedIndex ? 'bg-blue-100' : ''
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className={`text-xs px-1 py-0.5 rounded ${
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
                <span className="text-xs text-gray-500 truncate ml-2 max-w-[120px]">
                  {suggestion.description}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Input Chips */}
      <InputChips nodeId={nodeId} onInsert={insertText} />

      {/* Help Panel — compact, collapsible */}
      {showHelp && (
        <div className="space-y-2 pt-2 border-t border-gray-100">
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1">Functions</div>
            <div className="flex flex-wrap gap-1">
              {AVAILABLE_FUNCTIONS.map((func) => (
                <button
                  key={func.name}
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => insertText(func.example)}
                  className="px-1.5 py-0.5 text-xs font-mono bg-gray-50 text-gray-700 border border-gray-200 rounded hover:bg-purple-50 hover:text-purple-700 transition-colors"
                  title={func.description}
                >
                  {func.name}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1">Operators</div>
            <div className="flex flex-wrap gap-1.5 text-xs font-mono text-gray-600">
              {['+', '-', '*', '/', '**', '%', '>', '<', '=='].map((op) => (
                <span key={op} className="px-1 py-0.5 bg-gray-50 rounded border border-gray-200">
                  {op}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
