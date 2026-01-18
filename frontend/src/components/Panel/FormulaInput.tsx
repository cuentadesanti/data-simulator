import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { getEffectiveVarName } from '../../types/dag';

interface FormulaInputProps {
  value: string;
  onChange: (value: string) => void;
  nodeId: string;
  placeholder?: string;
  compact?: boolean;
}

interface ValidationError {
  message: string;
  type: 'syntax' | 'reference';
}

interface Suggestion {
  id: string;
  name: string;
  type: 'node' | 'constant' | 'function';
  insertText: string;
}

const FUNCTIONS = ['abs', 'min', 'max', 'sqrt', 'pow', 'exp', 'log', 'round', 'floor', 'ceil', 'clamp', 'if_else'];
const CONSTANTS = ['PI', 'E', 'TRUE', 'FALSE'];

export const FormulaInput: React.FC<FormulaInputProps> = ({
  value,
  onChange,
  nodeId,
  placeholder = 'e.g., parent_node * 2',
  compact = false,
}) => {
  const nodes = useDAGStore((state) => state.nodes);
  const edges = useDAGStore((state) => state.edges);
  const context = useDAGStore((state) => state.context);

  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Get parent nodes (connected via edges)
  const parentIds = useMemo(
    () => new Set(edges.filter((e) => e.target === nodeId).map((e) => e.source)),
    [edges, nodeId]
  );

  const availableVariables = useMemo(
    () =>
      nodes
        .filter((n) => parentIds.has(n.id))
        .map((n) => ({
          id: n.id,
          varName: getEffectiveVarName(n.data.config),
          name: n.data.config.name,
        })),
    [nodes, parentIds]
  );

  const contextKeys = useMemo(() => Object.keys(context), [context]);

  const availableVarSet = useMemo(
    () =>
      new Set([
        ...availableVariables.map((v) => v.varName),
        ...contextKeys,
        ...CONSTANTS,
      ]),
    [availableVariables, contextKeys]
  );

  // Validation
  const validateFormula = useCallback(
    (formula: string): ValidationError[] => {
      const errors: ValidationError[] = [];
      if (!formula.trim()) return errors;

      // Check parentheses
      let parenCount = 0;
      for (const char of formula) {
        if (char === '(') parenCount++;
        if (char === ')') parenCount--;
        if (parenCount < 0) {
          errors.push({ message: 'Mismatched parentheses', type: 'syntax' });
          break;
        }
      }
      if (parenCount > 0) {
        errors.push({ message: 'Unclosed parenthesis', type: 'syntax' });
      }

      // Check variable references
      const variablePattern = /\b([a-z_][a-z0-9_]*)\b(?!\s*\()/gi;
      const matches = formula.matchAll(variablePattern);
      const invalidVars = new Set<string>();

      for (const match of matches) {
        const varName = match[1];
        const lowerVar = varName.toLowerCase();
        if (!availableVarSet.has(varName) && !FUNCTIONS.includes(lowerVar)) {
          invalidVars.add(varName);
        }
      }

      if (invalidVars.size > 0) {
        errors.push({
          message: `Unknown: ${Array.from(invalidVars).join(', ')}`,
          type: 'reference',
        });
      }

      return errors;
    },
    [availableVarSet]
  );

  useEffect(() => {
    const errors = validateFormula(value);
    setValidationErrors(errors);
  }, [value, validateFormula]);

  // Build suggestions
  const allSuggestions = useMemo(
    (): Suggestion[] => [
      ...availableVariables.map((v) => ({
        id: v.varName,
        name: v.name,
        type: 'node' as const,
        insertText: v.varName,
      })),
      ...contextKeys.map((key) => ({
        id: key,
        name: key,
        type: 'node' as const,
        insertText: key,
      })),
      ...CONSTANTS.map((c) => ({
        id: c,
        name: c,
        type: 'constant' as const,
        insertText: c,
      })),
      ...FUNCTIONS.map((f) => ({
        id: f,
        name: f,
        type: 'function' as const,
        insertText: f + '(',
      })),
    ],
    [availableVariables, contextKeys]
  );

  const getCurrentWord = (text: string, position: number) => {
    const beforeCursor = text.slice(0, position);
    const match = beforeCursor.match(/[a-zA-Z_][a-zA-Z0-9_]*$/);
    return match ? match[0] : '';
  };

  const updateSuggestions = useCallback(
    (text: string, position: number) => {
      const currentWord = getCurrentWord(text, position).toLowerCase();
      if (currentWord.length === 0) {
        setShowSuggestions(false);
        return;
      }

      const filtered = allSuggestions.filter((s) =>
        s.id.toLowerCase().includes(currentWord)
      );

      if (filtered.length > 0) {
        setSuggestions(filtered.slice(0, 6));
        setSelectedIndex(0);
        setShowSuggestions(true);
      } else {
        setShowSuggestions(false);
      }
    },
    [allSuggestions]
  );

  const insertSuggestion = useCallback(
    (suggestion: Suggestion) => {
      const input = inputRef.current;
      if (!input) return;

      const position = input.selectionStart || 0;
      const currentWord = getCurrentWord(value, position);
      const beforeWord = value.slice(0, position - currentWord.length);
      const afterCursor = value.slice(position);

      const newValue = beforeWord + suggestion.insertText + afterCursor;
      onChange(newValue);
      setShowSuggestions(false);

      setTimeout(() => {
        input.focus();
        const newPos = beforeWord.length + suggestion.insertText.length;
        input.setSelectionRange(newPos, newPos);
      }, 0);
    },
    [value, onChange]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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
      case 'Tab':
      case 'Enter':
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

  const isValid = validationErrors.length === 0;
  const hasValue = value.trim().length > 0;

  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            updateSuggestions(e.target.value, e.target.selectionStart || 0);
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => updateSuggestions(value, inputRef.current?.selectionStart || 0)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder={placeholder}
          className={`flex-1 px-3 py-2 border rounded-md shadow-sm focus:ring-2 text-sm font-mono ${
            hasValue
              ? isValid
                ? 'border-green-300 focus:ring-green-500 focus:border-green-500'
                : 'border-red-300 focus:ring-red-500 focus:border-red-500'
              : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
          }`}
        />
        {hasValue && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}
          >
            {isValid ? '✓' : '!'}
          </span>
        )}
      </div>

      {/* Validation errors */}
      {!compact && validationErrors.length > 0 && (
        <div className="mt-1 text-xs text-red-600">
          {validationErrors.map((err, i) => (
            <div key={i}>{err.message}</div>
          ))}
        </div>
      )}

      {/* Autocomplete dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
          {suggestions.map((suggestion, index) => (
            <button
              key={suggestion.id + suggestion.type}
              type="button"
              onMouseDown={() => insertSuggestion(suggestion)}
              className={`w-full text-left px-3 py-1.5 flex items-center gap-2 text-sm hover:bg-blue-50 ${
                index === selectedIndex ? 'bg-blue-100' : ''
              }`}
            >
              <span
                className={`text-xs px-1 rounded ${
                  suggestion.type === 'node'
                    ? 'bg-blue-100 text-blue-700'
                    : suggestion.type === 'constant'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-purple-100 text-purple-700'
                }`}
              >
                {suggestion.type === 'node' ? 'var' : suggestion.type === 'constant' ? 'const' : 'fn'}
              </span>
              <span className="font-mono">{suggestion.id}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
