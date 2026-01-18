import { useState, useMemo } from 'react';

interface ScatterPlotViewProps {
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

interface Point {
  x: number;
  y: number;
  colorValue: string | number | null;
  index: number;
}

function computeCorrelation(xValues: number[], yValues: number[]): number {
  const n = xValues.length;
  if (n === 0) return 0;

  const meanX = xValues.reduce((a, b) => a + b, 0) / n;
  const meanY = yValues.reduce((a, b) => a + b, 0) / n;

  let numerator = 0;
  let sumSqX = 0;
  let sumSqY = 0;

  for (let i = 0; i < n; i++) {
    const dx = xValues[i] - meanX;
    const dy = yValues[i] - meanY;
    numerator += dx * dy;
    sumSqX += dx * dx;
    sumSqY += dy * dy;
  }

  const denominator = Math.sqrt(sumSqX * sumSqY);
  return denominator === 0 ? 0 : numerator / denominator;
}

// Interpolate between two colors
function interpolateColor(color1: string, color2: string, t: number): string {
  const c1 = parseInt(color1.slice(1), 16);
  const c2 = parseInt(color2.slice(1), 16);

  const r1 = (c1 >> 16) & 255;
  const g1 = (c1 >> 8) & 255;
  const b1 = c1 & 255;

  const r2 = (c2 >> 16) & 255;
  const g2 = (c2 >> 8) & 255;
  const b2 = c2 & 255;

  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);

  return `rgb(${r}, ${g}, ${b})`;
}

const ScatterPlot = ({
  data,
  xColumn,
  yColumn,
  colorByColumn,
  isColorNumeric,
}: {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  colorByColumn: string | null;
  isColorNumeric: boolean;
}) => {
  const { points, xMin, xMax, yMin, yMax, correlation, categories, colorMin, colorMax } =
    useMemo(() => {
      const pts: Point[] = [];
      const xVals: number[] = [];
      const yVals: number[] = [];
      const colorValues: (string | number)[] = [];

      data.forEach((row, index) => {
        const x = row[xColumn] as number;
        const y = row[yColumn] as number;
        if (
          x !== null &&
          x !== undefined &&
          !isNaN(x) &&
          y !== null &&
          y !== undefined &&
          !isNaN(y)
        ) {
          const colorValue = colorByColumn ? row[colorByColumn] : null;
          pts.push({ x, y, colorValue: colorValue as string | number | null, index });
          xVals.push(x);
          yVals.push(y);
          if (colorValue !== null && colorValue !== undefined) {
            colorValues.push(colorValue as string | number);
          }
        }
      });

      if (pts.length === 0) {
        return {
          points: [],
          xMin: 0,
          xMax: 1,
          yMin: 0,
          yMax: 1,
          correlation: 0,
          categories: [],
          colorMin: 0,
          colorMax: 1,
        };
      }

      const xMin = Math.min(...xVals);
      const xMax = Math.max(...xVals);
      const yMin = Math.min(...yVals);
      const yMax = Math.max(...yVals);
      const correlation = computeCorrelation(xVals, yVals);

      // Get categories or numeric range for color
      let categories: string[] = [];
      let colorMin = 0;
      let colorMax = 1;

      if (colorByColumn && colorValues.length > 0) {
        if (isColorNumeric) {
          const numericColors = colorValues.filter((v) => typeof v === 'number') as number[];
          colorMin = Math.min(...numericColors);
          colorMax = Math.max(...numericColors);
        } else {
          categories = [...new Set(colorValues.map((v) => String(v)))].sort();
        }
      }

      return { points: pts, xMin, xMax, yMin, yMax, correlation, categories, colorMin, colorMax };
    }, [data, xColumn, yColumn, colorByColumn, isColorNumeric]);

  const chartWidth = 450;
  const chartHeight = 350;
  const padding = { top: 20, right: 20, bottom: 50, left: 60 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  // Scaling functions
  const xScale = (x: number) => {
    const range = xMax - xMin || 1;
    return padding.left + ((x - xMin) / range) * innerWidth;
  };

  const yScale = (y: number) => {
    const range = yMax - yMin || 1;
    return chartHeight - padding.bottom - ((y - yMin) / range) * innerHeight;
  };

  // Get color for a point
  const getPointColor = (colorValue: string | number | null): string => {
    if (!colorByColumn || colorValue === null || colorValue === undefined) {
      return '#3b82f6';
    }

    if (isColorNumeric && typeof colorValue === 'number') {
      const t = colorMax === colorMin ? 0.5 : (colorValue - colorMin) / (colorMax - colorMin);
      return interpolateColor('#3b82f6', '#ef4444', t); // Blue to red gradient
    } else {
      const catIndex = categories.indexOf(String(colorValue));
      return CATEGORY_COLORS[catIndex % CATEGORY_COLORS.length];
    }
  };

  // Sample points if too many (for performance)
  const displayPoints =
    points.length > 1000
      ? points.filter((_, i) => i % Math.ceil(points.length / 1000) === 0)
      : points;

  // Correlation color
  const corrColor =
    correlation > 0.5 ? 'text-green-600' : correlation < -0.5 ? 'text-red-600' : 'text-gray-600';

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900">
          {yColumn} vs {xColumn}
          {colorByColumn && (
            <span className="text-gray-500 font-normal"> (colored by {colorByColumn})</span>
          )}
        </h4>
        <div className="flex gap-4 text-xs">
          <span className="text-gray-500">n={points.length}</span>
          <span className={corrColor}>r={correlation.toFixed(3)}</span>
        </div>
      </div>

      {/* Legend for categorical colors */}
      {colorByColumn && !isColorNumeric && categories.length > 0 && (
        <div className="flex flex-wrap gap-3 mb-3">
          {categories.map((cat, i) => (
            <div key={cat} className="flex items-center gap-1.5 text-xs">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
              />
              <span className="text-gray-600">{cat}</span>
            </div>
          ))}
        </div>
      )}

      {/* Legend for numeric gradient */}
      {colorByColumn && isColorNumeric && (
        <div className="flex items-center gap-2 mb-3 text-xs">
          <span className="text-gray-500">{colorByColumn}:</span>
          <span className="text-gray-600">{colorMin.toFixed(1)}</span>
          <div
            className="w-24 h-3 rounded"
            style={{
              background: 'linear-gradient(to right, #3b82f6, #ef4444)',
            }}
          />
          <span className="text-gray-600">{colorMax.toFixed(1)}</span>
        </div>
      )}

      <svg width={chartWidth} height={chartHeight} className="overflow-visible">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line
              x1={padding.left}
              y1={padding.top + t * innerHeight}
              x2={chartWidth - padding.right}
              y2={padding.top + t * innerHeight}
              stroke="#f3f4f6"
              strokeWidth={1}
            />
            <line
              x1={padding.left + t * innerWidth}
              y1={padding.top}
              x2={padding.left + t * innerWidth}
              y2={chartHeight - padding.bottom}
              stroke="#f3f4f6"
              strokeWidth={1}
            />
          </g>
        ))}

        {/* Axes */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={chartHeight - padding.bottom}
          stroke="#d1d5db"
          strokeWidth={1}
        />
        <line
          x1={padding.left}
          y1={chartHeight - padding.bottom}
          x2={chartWidth - padding.right}
          y2={chartHeight - padding.bottom}
          stroke="#d1d5db"
          strokeWidth={1}
        />

        {/* Points */}
        {displayPoints.map((point) => (
          <circle
            key={point.index}
            cx={xScale(point.x)}
            cy={yScale(point.y)}
            r={3}
            fill={getPointColor(point.colorValue)}
            opacity={0.7}
          >
            <title>
              {xColumn}: {point.x.toFixed(2)}, {yColumn}: {point.y.toFixed(2)}
              {colorByColumn && point.colorValue !== null
                ? `, ${colorByColumn}: ${point.colorValue}`
                : ''}
            </title>
          </circle>
        ))}

        {/* X-axis label */}
        <text
          x={padding.left + innerWidth / 2}
          y={chartHeight - 10}
          fontSize={11}
          fill="#6b7280"
          textAnchor="middle"
        >
          {xColumn}
        </text>

        {/* Y-axis label */}
        <text
          x={15}
          y={padding.top + innerHeight / 2}
          fontSize={11}
          fill="#6b7280"
          textAnchor="middle"
          transform={`rotate(-90, 15, ${padding.top + innerHeight / 2})`}
        >
          {yColumn}
        </text>

        {/* Axis value labels */}
        <text x={padding.left} y={chartHeight - 30} fontSize={9} fill="#9ca3af" textAnchor="start">
          {xMin.toFixed(1)}
        </text>
        <text
          x={chartWidth - padding.right}
          y={chartHeight - 30}
          fontSize={9}
          fill="#9ca3af"
          textAnchor="end"
        >
          {xMax.toFixed(1)}
        </text>
        <text
          x={padding.left - 5}
          y={chartHeight - padding.bottom}
          fontSize={9}
          fill="#9ca3af"
          textAnchor="end"
        >
          {yMin.toFixed(1)}
        </text>
        <text x={padding.left - 5} y={padding.top + 5} fontSize={9} fill="#9ca3af" textAnchor="end">
          {yMax.toFixed(1)}
        </text>
      </svg>

      {points.length > 1000 && (
        <p className="text-xs text-gray-400 mt-2">
          Showing {displayPoints.length} of {points.length} points
        </p>
      )}
    </div>
  );
};

export const ScatterPlotView = ({ data, columns, allColumns }: ScatterPlotViewProps) => {
  const [xColumn, setXColumn] = useState<string>(columns[0] || '');
  const [yColumn, setYColumn] = useState<string>(columns[1] || columns[0] || '');
  const [colorByColumn, setColorByColumn] = useState<string | null>(null);
  const [showMatrix, setShowMatrix] = useState(false);

  // Find categorical columns for coloring
  const categoricalColumns = useMemo(() => {
    if (!allColumns) return [];
    return allColumns.filter((col) => {
      if (columns.includes(col)) return false;
      const firstValue = data.find((row) => row[col] !== null && row[col] !== undefined)?.[col];
      return typeof firstValue === 'string' || typeof firstValue === 'boolean';
    });
  }, [data, columns, allColumns]);

  // Check if colorByColumn is numeric
  const isColorNumeric = useMemo(() => {
    if (!colorByColumn) return false;
    const firstValue = data.find(
      (row) => row[colorByColumn] !== null && row[colorByColumn] !== undefined
    )?.[colorByColumn];
    return typeof firstValue === 'number';
  }, [data, colorByColumn]);

  // Compute correlation matrix
  const correlationMatrix = useMemo(() => {
    if (!showMatrix || columns.length < 2) return null;

    const matrix: Record<string, Record<string, number>> = {};
    for (const col1 of columns) {
      matrix[col1] = {};
      for (const col2 of columns) {
        // Build aligned pairs of values
        const pairs: [number, number][] = [];
        data.forEach((row) => {
          const xVal = row[col1] as number;
          const yVal = row[col2] as number;
          if (!isNaN(xVal) && !isNaN(yVal)) {
            pairs.push([xVal, yVal]);
          }
        });
        const xVals = pairs.map(([x]) => x);
        const yVals = pairs.map(([, y]) => y);
        matrix[col1][col2] = computeCorrelation(xVals, yVals);
      }
    }
    return matrix;
  }, [data, columns, showMatrix]);

  if (columns.length < 2) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <p>Need at least 2 numeric columns for scatter plots</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="flex-shrink-0 p-4 bg-white border-b border-gray-200">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">X-axis:</label>
            <select
              value={xColumn}
              onChange={(e) => setXColumn(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Y-axis:</label>
            <select
              value={yColumn}
              onChange={(e) => setYColumn(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              const tmp = xColumn;
              setXColumn(yColumn);
              setYColumn(tmp);
            }}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Swap
          </button>

          {/* Color by selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Color by:</label>
            <select
              value={colorByColumn || ''}
              onChange={(e) => setColorByColumn(e.target.value || null)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">None</option>
              <optgroup label="Categorical">
                {categoricalColumns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Numeric (gradient)">
                {columns
                  .filter((c) => c !== xColumn && c !== yColumn)
                  .map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
              </optgroup>
            </select>
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showMatrix}
              onChange={(e) => setShowMatrix(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Correlation matrix
          </label>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        <div className="flex gap-6 flex-wrap">
          {/* Main scatter plot */}
          <ScatterPlot
            data={data}
            xColumn={xColumn}
            yColumn={yColumn}
            colorByColumn={colorByColumn}
            isColorNumeric={isColorNumeric}
          />

          {/* Correlation matrix */}
          {showMatrix && correlationMatrix && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="font-medium text-gray-900 mb-3">Correlation Matrix</h4>
              <div className="overflow-auto">
                <table className="text-xs">
                  <thead>
                    <tr>
                      <th className="p-1"></th>
                      {columns.map((col) => (
                        <th
                          key={col}
                          className="p-1 font-medium text-gray-600 max-w-[60px] truncate"
                          title={col}
                        >
                          {col.slice(0, 6)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {columns.map((row) => (
                      <tr key={row}>
                        <td
                          className="p-1 font-medium text-gray-600 max-w-[60px] truncate"
                          title={row}
                        >
                          {row.slice(0, 6)}
                        </td>
                        {columns.map((col) => {
                          const corr = correlationMatrix[row][col];
                          const intensity = Math.abs(corr);
                          const bgColor =
                            corr > 0
                              ? `rgba(34, 197, 94, ${intensity * 0.5})`
                              : `rgba(239, 68, 68, ${intensity * 0.5})`;
                          return (
                            <td
                              key={col}
                              className="p-1 text-center cursor-pointer hover:ring-2 hover:ring-blue-400"
                              style={{ backgroundColor: bgColor }}
                              onClick={() => {
                                setXColumn(col);
                                setYColumn(row);
                              }}
                              title={`${row} vs ${col}: r=${corr.toFixed(3)}`}
                            >
                              {corr.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-2">Click a cell to view that scatter plot</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
