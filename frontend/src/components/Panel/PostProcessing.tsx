import React from 'react';
import type { NodeConfig, PostProcessing as PostProcessingType } from '../../types/dag';
import { useDAGStore } from '../../stores/dagStore';

interface PostProcessingProps {
  nodeId: string;
  config: NodeConfig;
}

export const PostProcessing: React.FC<PostProcessingProps> = ({ nodeId, config }) => {
  const updateNode = useDAGStore((state) => state.updateNode);

  const postProcessing = config.post_processing || {};

  const handleChange = (field: keyof PostProcessingType, value: number | undefined) => {
    const newPostProcessing: PostProcessingType = {
      ...postProcessing,
      [field]: value,
    };

    // Remove undefined values
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
      // Set default values when enabling
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
    <div className="space-y-4">
      <div className="border-b border-gray-200 pb-2">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
          Post-Processing (Optional)
        </h3>
        <p className="text-xs text-gray-500 mt-1">Apply transformations to the generated values</p>
      </div>

      {/* Round Decimals */}
      <div className="space-y-2">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={isEnabled('round_decimals')}
            onChange={(e) => handleCheckboxChange('round_decimals', e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span className="ml-2 text-sm font-medium text-gray-700">Round Decimals</span>
        </label>
        {isEnabled('round_decimals') && (
          <div className="ml-6">
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Number of decimal places to round to (0-10)
            </p>
          </div>
        )}
      </div>

      {/* Clip Min */}
      <div className="space-y-2">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={isEnabled('clip_min')}
            onChange={(e) => handleCheckboxChange('clip_min', e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span className="ml-2 text-sm font-medium text-gray-700">Clip Minimum</span>
        </label>
        {isEnabled('clip_min') && (
          <div className="ml-6">
            <input
              type="number"
              value={postProcessing.clip_min ?? 0}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                handleChange('clip_min', isNaN(val) ? undefined : val);
              }}
              step="any"
              placeholder="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Minimum value allowed (values below will be clipped)
            </p>
          </div>
        )}
      </div>

      {/* Clip Max */}
      <div className="space-y-2">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={isEnabled('clip_max')}
            onChange={(e) => handleCheckboxChange('clip_max', e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span className="ml-2 text-sm font-medium text-gray-700">Clip Maximum</span>
        </label>
        {isEnabled('clip_max') && (
          <div className="ml-6">
            <input
              type="number"
              value={postProcessing.clip_max ?? 100}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                handleChange('clip_max', isNaN(val) ? undefined : val);
              }}
              step="any"
              placeholder="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Maximum value allowed (values above will be clipped)
            </p>
          </div>
        )}
      </div>

      {/* Missing Rate */}
      <div className="space-y-2">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={isEnabled('missing_rate')}
            onChange={(e) => handleCheckboxChange('missing_rate', e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span className="ml-2 text-sm font-medium text-gray-700">Missing Values</span>
        </label>
        {isEnabled('missing_rate') && (
          <div className="ml-6">
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Rate of missing values (0-1, e.g., 0.05 = 5% missing)
            </p>
          </div>
        )}
      </div>

      {/* Summary */}
      {Object.keys(postProcessing).length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-md p-3">
          <p className="text-xs text-green-800 font-medium mb-1">Active post-processing:</p>
          <ul className="text-xs text-green-700 space-y-0.5">
            {postProcessing.round_decimals !== undefined && (
              <li>Round to {postProcessing.round_decimals} decimals</li>
            )}
            {postProcessing.clip_min !== undefined && (
              <li>Clip minimum at {postProcessing.clip_min}</li>
            )}
            {postProcessing.clip_max !== undefined && (
              <li>Clip maximum at {postProcessing.clip_max}</li>
            )}
            {postProcessing.missing_rate !== undefined && (
              <li>{(postProcessing.missing_rate * 100).toFixed(1)}% missing values</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};
