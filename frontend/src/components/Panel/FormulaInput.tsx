import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { getEffectiveVarName } from '../../types/dag';
import { buildSuggestions, FORMULA_RESERVED_NAMES, type FormulaSuggestion } from '../../utils/buildSuggestions';

interface FormulaInputProps {
  value: string;
  onChange: (value: string) => void;
  nodeId: string;
  placeholder?: string;
  compact?: boolean;
  onBlurCapture?: () => void;
  onFocusCapture?: () => void;
}

interface ValidationError {
  message: string;
  type: 'syntax' | 'reference';
}

const CONSTANTS = ['PI', 'E', 'TRUE', 'FALSE'];

export const FormulaInput: React.FC<FormulaInputProps> = ({
  value,
  onChange,
  nodeId,
  placeholder = 'e.g., parent_node * 2',
  compact = false,
  onBlurCapture,
  onFocusCapture,
}) => {
  const nodes = useDAGStore((state) => state.nodes);
  const edges = useDAGStore((state) => state.edges);
  const context = useDAGStore((state) => state.context);
  const contextMeta = useDAGStore((state) => state.contextMeta);

  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<FormulaSuggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Get parent nodes (connected via edges)
  const parentIds = useMemo(
    () => new Set(edges.filter((e) => e.target === nodeId).map((e) => e.source)),
    [edges, nodeId]
  );

  const parentVariables = useMemo(
    () =>
      nodes
        .filter((n) => parentIds.has(n.id))
        .map((n) => ({
          varName: getEffectiveVarName(n.data.config),
          name: n.data.config.name,
          kind: n.data.config.kind,
          dtype: n.data.config.dtype || undefined,
          scope: n.data.config.scope,
        })),
    [nodes, parentIds]
  );

  const contextKeys = useMemo(() => Object.keys(context), [context]);

  const availableVarSet = useMemo(
    () =>
      new Set([
        ...parentVariables.map((v) => v.varName),
        ...contextKeys,
        ...CONSTANTS,
      ]),
    [parentVariables, contextKeys]
  );

  // Validation
  const validateFormula = useCallback(
    (formula: string): ValidationError[] => {
      const errors: ValidationError[] = [];
      if (!formula.trim()) return errors;

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

      const variablePattern = /\b([a-z_][a-z0-9_]*)\b(?!\s*\()/gi;
      const matches = formula.matchAll(variablePattern);
      const invalidVars = new Set<string>();

      for (const match of matches) {
        const varName = match[1];
        if (!availableVarSet.has(varName) && !FORMULA_RESERVED_NAMES.has(varName.toLowerCase())) {
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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- derived validation state synced from value changes
    setValidationErrors(errors);
  }, [value, validateFormula]);

  // Build suggestions using shared utility
  const allSuggestions = useMemo(
    () => buildSuggestions(parentVariables, context, contextMeta),
    [parentVariables, context, contextMeta]
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
    (suggestion: FormulaSuggestion) => {
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
          onFocus={() => {
            onFocusCapture?.();
            updateSuggestions(value, inputRef.current?.selectionStart || 0);
          }}
          onBlur={() => {
            setTimeout(() => setShowSuggestions(false), 150);
            onBlurCapture?.();
          }}
          placeholder={placeholder}
          className={compact
            ? `flex-1 px-2 py-1.5 border rounded-md text-sm font-mono focus:ring-1 ${
                hasValue
                  ? isValid
                    ? 'border-gray-200 focus:ring-blue-500 focus:border-blue-500'
                    : 'border-red-300 focus:ring-red-500 focus:border-red-500'
                  : 'border-gray-200 focus:ring-blue-500 focus:border-blue-500'
              }`
            : `flex-1 px-3 py-2 border rounded-md shadow-sm focus:ring-2 text-sm font-mono ${
                hasValue
                  ? isValid
                    ? 'border-green-300 focus:ring-green-500 focus:border-green-500'
                    : 'border-red-300 focus:ring-red-500 focus:border-red-500'
                  : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
              }`
          }
        />
        {hasValue && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${
              isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}
          >
            {isValid ? '\u2713' : '!'}
          </span>
        )}
      </div>

      {/* Validation errors */}
      {validationErrors.length > 0 && (
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
                    : suggestion.type === 'context'
                      ? 'bg-purple-100 text-purple-700'
                      : suggestion.type === 'constant'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-purple-100 text-purple-700'
                }`}
              >
                {suggestion.type === 'node'
                  ? 'var'
                  : suggestion.type === 'context'
                    ? 'ctx'
                    : suggestion.type === 'constant'
                      ? 'const'
                      : 'fn'}
              </span>
              <span className="font-mono">{suggestion.id}</span>
              {suggestion.description && (
                <span className="text-xs text-gray-500 ml-auto truncate max-w-[80px]">
                  {suggestion.description}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
