import { useState } from 'react';
import {
  useDAGStore,
  selectIsValidating,
  selectValidationErrors,
  selectLastValidationResult,
} from '../../stores/dagStore';

export const ValidationChips = () => {
  const [expanded, setExpanded] = useState(false);
  const isValidating = useDAGStore(selectIsValidating);
  const errors = useDAGStore(selectValidationErrors);
  const lastResult = useDAGStore(selectLastValidationResult);

  const chipClasses =
    lastResult === 'invalid'
      ? 'bg-red-100 text-red-700'
      : lastResult === 'valid'
        ? 'bg-green-100 text-green-700'
        : 'bg-amber-100 text-amber-700';

  return (
    <div className="relative flex items-center gap-2">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className={`rounded-full px-3 py-1 text-xs font-medium ${chipClasses}`}
      >
        {isValidating
          ? 'Validating...'
          : lastResult === 'invalid'
            ? `Invalid (${errors.length})`
            : lastResult === 'valid'
              ? 'Valid'
              : 'Not validated'}
      </button>

      {expanded && errors.length > 0 && (
        <div className="absolute left-0 top-[calc(100%+8px)] z-20 w-[min(36rem,90vw)] rounded-md border border-red-200 bg-white p-3 text-sm text-red-700 shadow-sm">
          <ul className="space-y-1">
            {errors.map((error, index) => (
              <li key={`${index}-${error}`}>{error}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
