import { useDAGStore, selectPreviewData, selectMetadata } from '../../stores/dagStore';

export const PreviewStats = () => {
  const previewData = useDAGStore(selectPreviewData);
  const metadata = useDAGStore(selectMetadata);

  if (!previewData || previewData.length === 0) {
    return null;
  }

  const rowCount = previewData.length;
  const columnCount = Object.keys(previewData[0] || {}).length;
  const seed = metadata.seed;

  return (
    <div className="flex items-center gap-6 px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium text-gray-700">Rows:</span>
        <span className="text-gray-900">{rowCount.toLocaleString()}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="font-medium text-gray-700">Columns:</span>
        <span className="text-gray-900">{columnCount}</span>
      </div>

      {seed !== undefined && (
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-700">Seed:</span>
          <span className="text-gray-900">{seed}</span>
        </div>
      )}

      <div className="ml-auto text-xs text-gray-500">Preview data generated successfully</div>
    </div>
  );
};
