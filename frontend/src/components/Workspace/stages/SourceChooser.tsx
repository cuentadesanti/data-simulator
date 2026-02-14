interface SourceChooserProps {
  onPick: (sourceType: 'dag' | 'upload') => void;
}

export const SourceChooser = ({ onPick }: SourceChooserProps) => {
  return (
    <div className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
      <button
        type="button"
        onClick={() => onPick('dag')}
        className="rounded-xl border border-gray-200 bg-white p-6 text-left hover:border-blue-300 hover:shadow-sm"
      >
        <h3 className="text-lg font-semibold text-gray-900">Build a DAG</h3>
        <p className="mt-2 text-sm text-gray-600">
          Define synthetic generators and dependencies using stochastic and deterministic nodes.
        </p>
      </button>
      <button
        type="button"
        onClick={() => onPick('upload')}
        className="rounded-xl border border-gray-200 bg-white p-6 text-left hover:border-blue-300 hover:shadow-sm"
      >
        <h3 className="text-lg font-semibold text-gray-900">Upload Dataset</h3>
        <p className="mt-2 text-sm text-gray-600">
          Import CSV or Parquet and run transforms/modeling directly from uploaded data.
        </p>
      </button>
    </div>
  );
};
