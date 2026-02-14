import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { Dropdown } from '../common/Dropdown';
import type { ContextVariableType } from '../../types/dag';

const RESERVED_NAMES = new Set([
  'PI', 'E', 'TRUE', 'FALSE',
  'abs', 'min', 'max', 'sqrt', 'pow', 'exp', 'log', 'log10',
  'sin', 'cos', 'tan', 'round', 'floor', 'ceil', 'clamp', 'if_else',
  'and', 'or', 'not', 'if', 'else', 'in', 'is',
  'None', 'True', 'False', 'def', 'class', 'return', 'import', 'lambda',
]);

const SNAKE_CASE_PATTERN = /^[a-z_][a-z0-9_]*$/;

const TYPE_OPTIONS = [
  { value: 'number' as ContextVariableType, label: 'Number' },
  { value: 'boolean' as ContextVariableType, label: 'Boolean' },
  { value: 'dict' as ContextVariableType, label: 'Dict' },
  { value: 'array' as ContextVariableType, label: 'Array' },
];

const BOOL_OPTIONS = [
  { value: 'true', label: 'true' },
  { value: 'false', label: 'false' },
];

function defaultValueForType(type: ContextVariableType): unknown {
  switch (type) {
    case 'number': return 0;
    case 'boolean': return false;
    case 'dict': return {};
    case 'array': return [];
    default: return null;
  }
}

function isNonEmpty(value: unknown, type: ContextVariableType): boolean {
  if (type === 'dict') return typeof value === 'object' && value !== null && Object.keys(value).length > 0;
  if (type === 'array') return Array.isArray(value) && value.length > 0;
  return false;
}

// ─── Dict Editor ─────────────────────────────────────────────────────────────

const DictEditor: React.FC<{
  value: Record<string, number>;
  onChange: (value: Record<string, number>) => void;
}> = ({ value, onChange }) => {
  const entries = Object.entries(value);

  const addEntry = () => {
    let key = 'key';
    let i = 1;
    while (key in value) { key = `key_${i++}`; }
    onChange({ ...value, [key]: 0 });
  };

  const updateKey = (oldKey: string, newKey: string) => {
    if (newKey === oldKey) return;
    const newDict: Record<string, number> = {};
    for (const [k, v] of Object.entries(value)) {
      newDict[k === oldKey ? newKey : k] = v;
    }
    onChange(newDict);
  };

  const updateValue = (key: string, num: number) => {
    onChange({ ...value, [key]: num });
  };

  const removeEntry = (key: string) => {
    const { [key]: _, ...rest } = value;
    onChange(rest);
  };

  return (
    <div className="space-y-1">
      {entries.map(([key, val]) => (
        <DictRow
          key={key}
          entryKey={key}
          entryValue={val}
          allKeys={Object.keys(value)}
          onKeyChange={(newKey) => updateKey(key, newKey)}
          onValueChange={(num) => updateValue(key, num)}
          onRemove={() => removeEntry(key)}
        />
      ))}
      <button
        type="button"
        onClick={addEntry}
        className="text-xs text-purple-600 hover:text-purple-700"
      >
        + Add entry
      </button>
    </div>
  );
};

const DictRow: React.FC<{
  entryKey: string;
  entryValue: number;
  allKeys: string[];
  onKeyChange: (newKey: string) => void;
  onValueChange: (num: number) => void;
  onRemove: () => void;
}> = ({ entryKey, entryValue, allKeys, onKeyChange, onValueChange, onRemove }) => {
  const [localKey, setLocalKey] = useState(entryKey);
  const [localVal, setLocalVal] = useState(String(entryValue));
  const [keyError, setKeyError] = useState('');
  const [valError, setValError] = useState('');

  useEffect(() => { setLocalKey(entryKey); }, [entryKey]);
  useEffect(() => { setLocalVal(String(entryValue)); }, [entryValue]);

  const commitKey = () => {
    const trimmed = localKey.trim();
    if (!trimmed) { setKeyError('key required'); return; }
    if (trimmed !== entryKey && allKeys.includes(trimmed)) { setKeyError('duplicate key'); return; }
    setKeyError('');
    onKeyChange(trimmed);
  };

  const commitVal = () => {
    if (localVal.trim() === '') { setValError(''); onValueChange(0); return; }
    const num = Number(localVal);
    if (!isFinite(num)) { setValError('must be a number'); return; }
    setValError('');
    onValueChange(num);
  };

  return (
    <div className="flex items-center gap-1">
      <input
        type="text"
        value={localKey}
        onChange={(e) => { setLocalKey(e.target.value); setKeyError(''); }}
        onBlur={commitKey}
        className={`w-20 px-1.5 py-1 border rounded text-xs font-mono ${keyError ? 'border-red-300' : 'border-gray-200'}`}
        placeholder="key"
        title={keyError || undefined}
      />
      <span className="text-gray-400 text-xs">&rarr;</span>
      <input
        type="number"
        value={localVal}
        onChange={(e) => { setLocalVal(e.target.value); setValError(''); }}
        onBlur={commitVal}
        className={`w-20 px-1.5 py-1 border rounded text-xs font-mono ${valError ? 'border-red-300' : 'border-gray-200'}`}
        placeholder="0"
        title={valError || undefined}
      />
      <button
        type="button"
        onClick={onRemove}
        className="text-gray-400 hover:text-red-500 text-xs px-1"
        title="Remove"
      >
        &times;
      </button>
    </div>
  );
};

// ─── Array Editor ────────────────────────────────────────────────────────────

const ArrayEditor: React.FC<{
  value: number[];
  onChange: (value: number[]) => void;
}> = ({ value, onChange }) => {
  const addItem = () => onChange([...value, 0]);

  const updateItem = (index: number, num: number) => {
    const newArr = [...value];
    newArr[index] = num;
    onChange(newArr);
  };

  const removeItem = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-1">
      {value.map((item, index) => (
        <ArrayRow
          key={index}
          value={item}
          onValueChange={(num) => updateItem(index, num)}
          onRemove={() => removeItem(index)}
        />
      ))}
      <button
        type="button"
        onClick={addItem}
        className="text-xs text-purple-600 hover:text-purple-700"
      >
        + Add item
      </button>
    </div>
  );
};

const ArrayRow: React.FC<{
  value: number;
  onValueChange: (num: number) => void;
  onRemove: () => void;
}> = ({ value, onValueChange, onRemove }) => {
  const [localVal, setLocalVal] = useState(String(value));
  const [error, setError] = useState('');

  useEffect(() => { setLocalVal(String(value)); }, [value]);

  const commit = () => {
    if (localVal.trim() === '') { setError(''); onValueChange(0); return; }
    const num = Number(localVal);
    if (!isFinite(num)) { setError('must be a number'); return; }
    setError('');
    onValueChange(num);
  };

  return (
    <div className="flex items-center gap-1">
      <input
        type="number"
        value={localVal}
        onChange={(e) => { setLocalVal(e.target.value); setError(''); }}
        onBlur={commit}
        className={`flex-1 px-1.5 py-1 border rounded text-xs font-mono ${error ? 'border-red-300' : 'border-gray-200'}`}
        placeholder="0"
        title={error || undefined}
      />
      <button
        type="button"
        onClick={onRemove}
        className="text-gray-400 hover:text-red-500 text-xs px-1"
        title="Remove"
      >
        &times;
      </button>
    </div>
  );
};

// ─── Variable Row ────────────────────────────────────────────────────────────

const VariableRow: React.FC<{
  varKey: string;
  allKeys: string[];
}> = ({ varKey, allKeys }) => {
  const context = useDAGStore((s) => s.context);
  const contextMeta = useDAGStore((s) => s.contextMeta);
  const setContextVariable = useDAGStore((s) => s.setContextVariable);
  const renameContextVariable = useDAGStore((s) => s.renameContextVariable);
  const deleteContextEntry = useDAGStore((s) => s.deleteContextEntry);

  const value = context[varKey];
  const meta = contextMeta[varKey];
  const type = meta?.type ?? 'unsupported';

  const [localName, setLocalName] = useState(varKey);
  const [nameError, setNameError] = useState('');
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const deleteTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { setLocalName(varKey); }, [varKey]);

  const validateName = (name: string): string => {
    if (!name.trim()) return 'Name required';
    if (!SNAKE_CASE_PATTERN.test(name)) return 'Must be snake_case';
    if (RESERVED_NAMES.has(name)) return 'Reserved name';
    if (name !== varKey && allKeys.includes(name)) return 'Name already used';
    return '';
  };

  const commitName = () => {
    const trimmed = localName.trim();
    const error = validateName(trimmed);
    setNameError(error);
    if (!error && trimmed !== varKey) {
      renameContextVariable(varKey, trimmed);
    }
  };

  const handleTypeChange = (newType: ContextVariableType) => {
    if (newType === type) return;
    if (isNonEmpty(value, type as ContextVariableType)) {
      if (!window.confirm(`Changing type will reset the value. Continue?`)) return;
    }
    setContextVariable(varKey, defaultValueForType(newType), newType);
  };

  const handleDelete = () => {
    if (confirmingDelete) {
      if (deleteTimeoutRef.current) clearTimeout(deleteTimeoutRef.current);
      deleteContextEntry(varKey);
    } else {
      setConfirmingDelete(true);
      deleteTimeoutRef.current = setTimeout(() => setConfirmingDelete(false), 2000);
    }
  };

  return (
    <div className="border border-gray-200 rounded-md p-2.5 space-y-2">
      {/* Name + type + delete */}
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          value={localName}
          onChange={(e) => { setLocalName(e.target.value); setNameError(''); }}
          onBlur={commitName}
          className={`flex-1 px-1.5 py-1 border rounded text-xs font-mono ${
            nameError ? 'border-red-300' : 'border-gray-200'
          }`}
          placeholder="variable_name"
          title={nameError || undefined}
        />
        {type !== 'unsupported' && (
          <Dropdown<ContextVariableType>
            options={TYPE_OPTIONS}
            value={type as ContextVariableType}
            onChange={handleTypeChange}
            size="sm"
            className="w-24"
          />
        )}
        <button
          type="button"
          onClick={handleDelete}
          className={`text-xs px-1.5 py-1 rounded ${
            confirmingDelete
              ? 'bg-red-100 text-red-700'
              : 'text-gray-400 hover:text-red-500'
          }`}
          title={confirmingDelete ? 'Click again to confirm' : 'Delete variable'}
        >
          {confirmingDelete ? 'Delete?' : '\u2715'}
        </button>
      </div>
      {nameError && <div className="text-xs text-red-600">{nameError}</div>}

      {/* Value editor by type */}
      {type === 'number' && (
        <NumberEditor value={value as number} onChange={(v) => setContextVariable(varKey, v, 'number')} />
      )}
      {type === 'boolean' && (
        <Dropdown
          options={BOOL_OPTIONS}
          value={String(value)}
          onChange={(v) => setContextVariable(varKey, v === 'true', 'boolean')}
          size="sm"
        />
      )}
      {type === 'dict' && (
        <DictEditor
          value={(value ?? {}) as Record<string, number>}
          onChange={(v) => setContextVariable(varKey, v, 'dict')}
        />
      )}
      {type === 'array' && (
        <ArrayEditor
          value={(value ?? []) as number[]}
          onChange={(v) => setContextVariable(varKey, v, 'array')}
        />
      )}
      {type === 'unsupported' && (
        <div className="px-2 py-1.5 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          <p className="font-medium mb-1">Unsupported variable type</p>
          <pre className="font-mono text-xs text-gray-600 truncate">
            {JSON.stringify(value, null, 0)?.slice(0, 100)}
          </pre>
          <p className="mt-1">Delete and recreate as a supported type.</p>
        </div>
      )}
    </div>
  );
};

// ─── Number Editor ───────────────────────────────────────────────────────────

const NumberEditor: React.FC<{
  value: number;
  onChange: (value: number) => void;
}> = ({ value, onChange }) => {
  const [localVal, setLocalVal] = useState(String(value));
  const [error, setError] = useState('');

  useEffect(() => { setLocalVal(String(value)); }, [value]);

  const commit = () => {
    if (localVal.trim() === '') { setError(''); onChange(0); return; }
    const num = Number(localVal);
    if (!isFinite(num)) { setError('Must be a finite number'); return; }
    setError('');
    onChange(num);
  };

  return (
    <div>
      <input
        type="number"
        value={localVal}
        onChange={(e) => { setLocalVal(e.target.value); setError(''); }}
        onBlur={commit}
        className={`w-full px-1.5 py-1 border rounded text-xs font-mono ${
          error ? 'border-red-300' : 'border-gray-200'
        }`}
        placeholder="0"
      />
      {error && <div className="text-xs text-red-600 mt-0.5">{error}</div>}
    </div>
  );
};

// ─── Variables Panel ─────────────────────────────────────────────────────────

export const VariablesPanel: React.FC = () => {
  const context = useDAGStore((s) => s.context);
  const setContextVariable = useDAGStore((s) => s.setContextVariable);

  const keys = Object.keys(context);

  const handleAdd = useCallback(() => {
    let name = 'new_var';
    let i = 1;
    while (name in context) { name = `new_var_${i++}`; }
    setContextVariable(name, 0, 'number');
  }, [context, setContextVariable]);

  return (
    <div className="w-full h-full bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900">Variables</span>
          {keys.length > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">
              {keys.length}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleAdd}
          className="text-xs px-2 py-1 rounded-md bg-purple-50 text-purple-700 hover:bg-purple-100 font-medium"
        >
          + Add
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {keys.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            <p>No variables defined.</p>
            <p className="mt-1 text-xs">Add one to use in formulas and distribution params.</p>
          </div>
        ) : (
          <div className="p-3 space-y-2">
            {keys.map((key) => (
              <VariableRow key={key} varKey={key} allKeys={keys} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
