import { useState, useMemo } from 'react';

interface HistogramViewProps {
  data: Record<string, unknown>[];
  columns: string[]; // numeric columns
  allColumns?: string[]; // all columns including categorical
}

// Color palette for categories
const CATEGORY_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
  '#6366f1', // indigo
];

interface StackedBin {
  start: number;
  end: number;
  counts: Record<string, number>; // category -> count
  total: number;
}

interface GroupedHistogramData {
  bins: StackedBin[];
  min: number;
  max: number;
  categories: string[];
  statsByCategory: Record<string, { mean: number; std: number; n: number }>;
}

function computeGroupedHistogram(
  data: Record<string, unknown>[],
  valueColumn: string,
  groupByColumn: string | null,
  numBins: number = 20
): GroupedHistogramData {
  // Extract values with their categories
  const pairs: { value: number; category: string }[] = [];

  data.forEach((row) => {
    const value = row[valueColumn] as number;
    if (value !== null && value !== undefined && !isNaN(value)) {
      const category = groupByColumn ? String(row[groupByColumn] ?? 'Unknown') : 'All';
      pairs.push({ value, category });
    }
  });

  if (pairs.length === 0) {
    return { bins: [], min: 0, max: 0, categories: [], statsByCategory: {} };
  }

  // Get unique categories
  const categories = [...new Set(pairs.map((p) => p.category))].sort();

  // Compute stats per category
  const statsByCategory: Record<string, { mean: number; std: number; n: number }> = {};
  for (const cat of categories) {
    const values = pairs.filter((p) => p.category === cat).map((p) => p.value);
    const n = values.length;
    const mean = values.reduce((a, b) => a + b, 0) / n;
    const std = Math.sqrt(values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n);
    statsByCategory[cat] = { mean, std, n };
  }

  // Compute bins
  const allValues = pairs.map((p) => p.value);
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);

  if (min === max) {
    const counts: Record<string, number> = {};
    for (const cat of categories) {
      counts[cat] = pairs.filter((p) => p.category === cat).length;
    }
    return {
      bins: [{ start: min - 0.5, end: max + 0.5, counts, total: pairs.length }],
      min,
      max,
      categories,
      statsByCategory,
    };
  }

  const binWidth = (max - min) / numBins;
  const bins: StackedBin[] = [];

  for (let i = 0; i < numBins; i++) {
    const counts: Record<string, number> = {};
    for (const cat of categories) {
      counts[cat] = 0;
    }
    bins.push({
      start: min + i * binWidth,
      end: min + (i + 1) * binWidth,
      counts,
      total: 0,
    });
  }

  for (const { value, category } of pairs) {
    const binIndex = Math.min(Math.floor((value - min) / binWidth), numBins - 1);
    bins[binIndex].counts[category]++;
    bins[binIndex].total++;
  }

  return { bins, min, max, categories, statsByCategory };
}

const GroupedHistogram = ({
  column,
  data,
  groupByColumn,
}: {
  column: string;
  data: Record<string, unknown>[];
  groupByColumn: string | null;
}) => {
  const histogram = useMemo(() => {
    return computeGroupedHistogram(data, column, groupByColumn);
  }, [data, column, groupByColumn]);

  if (histogram.bins.length === 0) {
    return <div className="p-4 text-center text-gray-500">No valid numeric data for {column}</div>;
  }

  const maxTotal = Math.max(...histogram.bins.map((b) => b.total));
  const chartWidth = 320;
  const chartHeight = 180;
  const padding = { top: 10, right: 10, bottom: 30, left: 40 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;
  const barWidth = innerWidth / histogram.bins.length;

  const isGrouped = groupByColumn !== null;
  const categories = histogram.categories;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-gray-900">{column}</h4>
        <span className="text-xs text-gray-500">n={data.length}</span>
      </div>

      {/* Legend for grouped histogram */}
      {isGrouped && categories.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {categories.map((cat, i) => (
            <div key={cat} className="flex items-center gap-1 text-xs">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
              />
              <span className="text-gray-600">{cat}</span>
              <span className="text-gray-400">(n={histogram.statsByCategory[cat]?.n})</span>
            </div>
          ))}
        </div>
      )}

      <svg width={chartWidth} height={chartHeight} className="overflow-visible">
        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={chartHeight - padding.bottom}
          stroke="#e5e7eb"
          strokeWidth={1}
        />
        {/* X-axis */}
        <line
          x1={padding.left}
          y1={chartHeight - padding.bottom}
          x2={chartWidth - padding.right}
          y2={chartHeight - padding.bottom}
          stroke="#e5e7eb"
          strokeWidth={1}
        />

        {/* Stacked Bars */}
        {histogram.bins.map((bin, i) => {
          let yOffset = 0;
          return (
            <g key={i}>
              {categories.map((cat, catIndex) => {
                const count = bin.counts[cat] || 0;
                const barHeight = maxTotal > 0 ? (count / maxTotal) * innerHeight : 0;
                const y = chartHeight - padding.bottom - yOffset - barHeight;
                yOffset += barHeight;

                return (
                  <rect
                    key={cat}
                    x={padding.left + i * barWidth + 1}
                    y={y}
                    width={Math.max(barWidth - 2, 1)}
                    height={barHeight}
                    fill={CATEGORY_COLORS[catIndex % CATEGORY_COLORS.length]}
                    opacity={0.8}
                  >
                    <title>{`${cat}: ${count}`}</title>
                  </rect>
                );
              })}
            </g>
          );
        })}

        {/* X-axis labels */}
        <text x={padding.left} y={chartHeight - 5} fontSize={10} fill="#6b7280" textAnchor="start">
          {histogram.min.toFixed(1)}
        </text>
        <text
          x={chartWidth - padding.right}
          y={chartHeight - 5}
          fontSize={10}
          fill="#6b7280"
          textAnchor="end"
        >
          {histogram.max.toFixed(1)}
        </text>

        {/* Y-axis labels */}
        <text
          x={padding.left - 5}
          y={padding.top + 5}
          fontSize={10}
          fill="#6b7280"
          textAnchor="end"
        >
          {maxTotal}
        </text>
        <text
          x={padding.left - 5}
          y={chartHeight - padding.bottom}
          fontSize={10}
          fill="#6b7280"
          textAnchor="end"
        >
          0
        </text>
      </svg>

      {/* Stats per category */}
      {isGrouped && categories.length > 1 && (
        <div className="mt-2 grid grid-cols-2 gap-1 text-xs">
          {categories.slice(0, 4).map((cat, i) => (
            <div key={cat} className="flex items-center gap-1">
              <div
                className="w-2 h-2 rounded-sm flex-shrink-0"
                style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
              />
              <span className="text-gray-500 truncate" title={cat}>
                μ={histogram.statsByCategory[cat]?.mean.toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Overall stats when not grouped */}
      {!isGrouped && (
        <div className="mt-2 flex justify-between text-xs text-gray-400">
          <span>μ={histogram.statsByCategory['All']?.mean.toFixed(2)}</span>
          <span>σ={histogram.statsByCategory['All']?.std.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
};

export const HistogramView = ({ data, columns, allColumns }: HistogramViewProps) => {
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set(columns.slice(0, 6)));
  const [groupByColumn, setGroupByColumn] = useState<string | null>(null);

  // Find categorical columns (non-numeric)
  const categoricalColumns = useMemo(() => {
    if (!allColumns) return [];
    return allColumns.filter((col) => {
      if (columns.includes(col)) return false; // Skip numeric columns
      const firstValue = data.find((row) => row[col] !== null && row[col] !== undefined)?.[col];
      return typeof firstValue === 'string' || typeof firstValue === 'boolean';
    });
  }, [data, columns, allColumns]);

  const toggleColumn = (col: string) => {
    setSelectedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(col)) {
        next.delete(col);
      } else {
        next.add(col);
      }
      return next;
    });
  };

  const selectAll = () => setSelectedColumns(new Set(columns));
  const selectNone = () => setSelectedColumns(new Set());

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="flex-shrink-0 p-4 bg-white border-b border-gray-200 space-y-3">
        {/* Group by selector */}
        {categoricalColumns.length > 0 && (
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Group by:</label>
            <select
              value={groupByColumn || ''}
              onChange={(e) => setGroupByColumn(e.target.value || null)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">None (single color)</option>
              {categoricalColumns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
            {groupByColumn && (
              <span className="text-xs text-gray-500">
                Stacked bars show distribution per category
              </span>
            )}
          </div>
        )}

        {/* Column selector */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-gray-700">Show columns:</span>
            <button onClick={selectAll} className="text-xs text-blue-600 hover:text-blue-800">
              All
            </button>
            <span className="text-gray-300">|</span>
            <button onClick={selectNone} className="text-xs text-blue-600 hover:text-blue-800">
              None
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {columns.map((col) => (
              <button
                key={col}
                onClick={() => toggleColumn(col)}
                className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                  selectedColumns.has(col)
                    ? 'bg-blue-100 border-blue-300 text-blue-700'
                    : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
                }`}
              >
                {col}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Histograms grid */}
      <div className="flex-1 overflow-auto p-4">
        {selectedColumns.size === 0 ? (
          <div className="text-center text-gray-500 py-8">
            Select columns above to view histograms
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {columns
              .filter((col) => selectedColumns.has(col))
              .map((col) => (
                <GroupedHistogram
                  key={`${col}-${groupByColumn}`}
                  column={col}
                  data={data}
                  groupByColumn={groupByColumn}
                />
              ))}
          </div>
        )}
      </div>
    </div>
  );
};
