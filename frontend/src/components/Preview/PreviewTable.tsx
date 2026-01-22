import { useState, useMemo } from 'react';

interface PreviewTableProps {
  data: Record<string, unknown>[];
  columns?: string[] | null;
  /** Columns to visually highlight (e.g., derived columns in pipeline view) */
  highlightColumns?: string[];
}

type SortConfig = {
  key: string;
  direction: 'asc' | 'desc';
} | null;

type DataType = 'float' | 'int' | 'category' | 'bool' | 'string';

const detectColumnType = (values: unknown[]): DataType => {
  // Sample first few non-null values
  const samples = values.filter((v) => v !== null && v !== undefined).slice(0, 100);

  if (samples.length === 0) return 'string';

  const allBooleans = samples.every((v) => typeof v === 'boolean');
  if (allBooleans) return 'bool';

  const allNumbers = samples.every((v) => typeof v === 'number');
  if (allNumbers) {
    const allIntegers = samples.every((v) => Number.isInteger(v as number));
    return allIntegers ? 'int' : 'float';
  }

  const allStrings = samples.every((v) => typeof v === 'string');
  if (allStrings) {
    const uniqueCount = new Set(samples).size;
    // If less than 20% unique values, consider it categorical
    return uniqueCount < samples.length * 0.2 ? 'category' : 'string';
  }

  return 'string';
};

const formatValue = (value: unknown, type: DataType): string => {
  if (value === null || value === undefined) {
    return 'null';
  }

  if (type === 'float' && typeof value === 'number') {
    return value.toFixed(2);
  }

  if (type === 'int' && typeof value === 'number') {
    return Math.round(value).toString();
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }

  return String(value);
};

const getTypeIcon = (type: DataType): string => {
  switch (type) {
    case 'float':
      return '1.23';
    case 'int':
      return '123';
    case 'category':
      return 'ABC';
    case 'bool':
      return 'T/F';
    case 'string':
      return 'Aa';
  }
};

const getTypeColor = (type: DataType): string => {
  switch (type) {
    case 'float':
      return 'text-blue-600 bg-blue-50';
    case 'int':
      return 'text-green-600 bg-green-50';
    case 'category':
      return 'text-purple-600 bg-purple-50';
    case 'bool':
      return 'text-orange-600 bg-orange-50';
    case 'string':
      return 'text-gray-600 bg-gray-50';
  }
};

export const PreviewTable = ({ data, columns: columnOrder, highlightColumns = [] }: PreviewTableProps) => {
  const [sortConfig, setSortConfig] = useState<SortConfig>(null);

  const highlightSet = useMemo(() => new Set(highlightColumns), [highlightColumns]);

  // Extract columns and detect types
  // Use columnOrder from backend (topological order) if available, otherwise fallback to Object.keys
  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];
    const keys = columnOrder && columnOrder.length > 0 ? columnOrder : Object.keys(data[0]);
    return keys.map((key) => {
      const values = data.map((row) => row[key]);
      const type = detectColumnType(values);
      return { key, type };
    });
  }, [data, columnOrder]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortConfig) return data;

    const sorted = [...data].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];

      // Handle nulls
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      // Compare values
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal);
      const bStr = String(bVal);
      const comparison = aStr.localeCompare(bStr);
      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [data, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (!current || current.key !== key) {
        return { key, direction: 'asc' };
      }
      if (current.direction === 'asc') {
        return { key, direction: 'desc' };
      }
      return null;
    });
  };

  const getSortIcon = (key: string) => {
    if (!sortConfig || sortConfig.key !== key) {
      return (
        <svg
          className="w-4 h-4 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
          />
        </svg>
      );
    }

    if (sortConfig.direction === 'asc') {
      return (
        <svg
          className="w-4 h-4 text-blue-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      );
    }

    return (
      <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  return (
    <div className="overflow-auto flex-1">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 sticky top-0 z-10">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-100 sticky left-0 z-20">
              #
            </th>
            {columns.map(({ key, type }) => {
              const isHighlighted = highlightSet.has(key);
              return (
                <th
                  key={key}
                  className={`px-4 py-3 text-left cursor-pointer hover:bg-gray-100 transition-colors ${isHighlighted ? 'bg-blue-50 border-l-2 border-blue-400' : ''
                    }`}
                  onClick={() => handleSort(key)}
                >
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${isHighlighted ? 'text-blue-700' : 'text-gray-900'}`}>
                      {key}
                    </span>
                    {isHighlighted && (
                      <span className="px-1 py-0.5 bg-blue-100 text-blue-600 text-xs rounded font-medium">
                        new
                      </span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${getTypeColor(type)}`}>
                      {getTypeIcon(type)}
                    </span>
                    {getSortIcon(key)}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedData.map((row, rowIndex) => (
            <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              <td className="px-4 py-2 text-xs text-gray-500 bg-gray-50 sticky left-0 font-medium">
                {rowIndex + 1}
              </td>
              {columns.map(({ key, type }) => {
                const value = row[key];
                const isNull = value === null || value === undefined;
                return (
                  <td
                    key={key}
                    className={`px-4 py-2 whitespace-nowrap ${isNull ? 'text-gray-400 italic' : 'text-gray-900'
                      }`}
                  >
                    {formatValue(value, type)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
