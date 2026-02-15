import React, { useState, useMemo } from 'react';
import type { NodeConfig, PostProcessing as PostProcessingType } from '../../types/dag';
import { useDAGStore } from '../../stores/dagStore';

interface PostProcessingProps {
  nodeId: string;
  config: NodeConfig;
}

export const PostProcessing: React.FC<PostProcessingProps> = ({ nodeId, config }) => {
  const updateNode = useDAGStore((state) => state.updateNode);

  const postProcessing = config.post_processing || {};

  const hasActiveOptions = Object.keys(postProcessing).length > 0;

  const [expanded, setExpanded] = useState(() => hasActiveOptions);

  // Auto-expand when options become active externally
  React.useEffect(() => {
    if (hasActiveOptions) {
      setExpanded(true);
    }
  }, [hasActiveOptions]);

  const summary = useMemo(() => {
    const parts = [
      postProcessing.round_decimals != null && `Round ${postProcessing.round_decimals}`,
      postProcessing.clip_min != null && `Min ${postProcessing.clip_min}`,
      postProcessing.clip_max != null && `Max ${postProcessing.clip_max}`,
      postProcessing.missing_rate != null &&
        `${(postProcessing.missing_rate * 100).toFixed(0)}% missing`,
    ].filter(Boolean);
    return parts.join(' \u00b7 ');
  }, [postProcessing]);

  const handleChange = (field: keyof PostProcessingType, value: number | undefined) => {
    const newPostProcessing: PostProcessingType = {
      ...postProcessing,
      [field]: value,
    };

    Object.keys(newPostProcessing).forEach((key) => {
      if (newPostProcessing[key as keyof PostProcessingType] === undefined) {
        delete newPostProcessing[key as keyof PostProcessingType];
      }
    });

    updateNode(nodeId, {
      post_processing: Object.keys(newPostProcessing).length > 0 ? newPostProcessing : undefined,
    });
  };

  const handleCheckboxChange = (field: keyof PostProcessingType, checked: boolean) => {
    if (!checked) {
      handleChange(field, undefined);
    } else {
      const defaults: Record<string, number> = {
        round_decimals: 2,
        clip_min: 0,
        clip_max: 100,
        missing_rate: 0.05,
      };
      handleChange(field, defaults[field]);
    }
  };

  const isEnabled = (field: keyof PostProcessingType) => {
    return postProcessing[field] !== undefined;
  };

  return (
    <div>
      {/* Collapse toggle header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="flex items-center gap-1.5 w-full text-left py-1"
      >
        <svg
          className={`w-3 h-3 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-xs font-medium text-gray-700">Post-Processing</span>
        {!expanded && summary && (
          <span className="text-xs text-gray-400 ml-1 truncate">{summary}</span>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-2 space-y-3 pl-4.5">
          {/* Round Decimals */}
          <div className="space-y-1.5">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isEnabled('round_decimals')}
                onChange={(e) => handleCheckboxChange('round_decimals', e.target.checked)}
                className="h-3.5 w-3.5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-xs text-gray-700">Round Decimals</span>
            </label>
            {isEnabled('round_decimals') && (
              <input
                type="number"
                value={postProcessing.round_decimals ?? 2}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  handleChange('round_decimals', isNaN(val) ? undefined : val);
                }}
                min={0}
                max={10}
                step={1}
                placeholder="2"
                className="ml-5.5 w-20 px-2 py-1 border border-gray-200 rounded-md text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            )}
          </div>

          {/* Clip Min */}
          <div className="space-y-1.5">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isEnabled('clip_min')}
                onChange={(e) => handleCheckboxChange('clip_min', e.target.checked)}
                className="h-3.5 w-3.5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-xs text-gray-700">Clip Min</span>
            </label>
            {isEnabled('clip_min') && (
              <input
                type="number"
                value={postProcessing.clip_min ?? 0}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  handleChange('clip_min', isNaN(val) ? undefined : val);
                }}
                step="any"
                placeholder="0"
                className="ml-5.5 w-20 px-2 py-1 border border-gray-200 rounded-md text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            )}
          </div>

          {/* Clip Max */}
          <div className="space-y-1.5">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isEnabled('clip_max')}
                onChange={(e) => handleCheckboxChange('clip_max', e.target.checked)}
                className="h-3.5 w-3.5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-xs text-gray-700">Clip Max</span>
            </label>
            {isEnabled('clip_max') && (
              <input
                type="number"
                value={postProcessing.clip_max ?? 100}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  handleChange('clip_max', isNaN(val) ? undefined : val);
                }}
                step="any"
                placeholder="100"
                className="ml-5.5 w-20 px-2 py-1 border border-gray-200 rounded-md text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            )}
          </div>

          {/* Missing Rate */}
          <div className="space-y-1.5">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isEnabled('missing_rate')}
                onChange={(e) => handleCheckboxChange('missing_rate', e.target.checked)}
                className="h-3.5 w-3.5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-xs text-gray-700">Missing Values</span>
            </label>
            {isEnabled('missing_rate') && (
              <input
                type="number"
                value={postProcessing.missing_rate ?? 0.05}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  handleChange('missing_rate', isNaN(val) ? undefined : val);
                }}
                min={0}
                max={1}
                step={0.01}
                placeholder="0.05"
                className="ml-5.5 w-20 px-2 py-1 border border-gray-200 rounded-md text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
