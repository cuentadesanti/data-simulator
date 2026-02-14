import { useCallback, useEffect, useRef } from 'react';
import { DAGCanvas } from '../../Canvas';
import { SourceChooser } from './SourceChooser';
import { UploadWizard } from './UploadWizard';
import { useSourceStore } from '../../../stores/sourceStore';
import { useDAGStore, selectNodes } from '../../../stores/dagStore';
import { useProjectStore } from '../../../stores/projectStore';
import { ValidationChips } from '../ValidationChips';
import { useAutoValidation } from '../../../hooks/useAutoValidation';
import { trackFlowStart } from '../../../services/telemetry';

export const SourceStage = () => {
  const sourceType = useSourceStore((state) => state.sourceType);
  const setSourceType = useSourceStore((state) => state.setSourceType);
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const setProjectSourceType = useProjectStore((state) => state.setProjectSourceType);
  const nodes = useDAGStore(selectNodes);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (!initializedRef.current && !sourceType && nodes.length > 0) {
      setSourceType('dag');
    }
    initializedRef.current = true;
  }, [sourceType, nodes.length, setSourceType]);

  const handlePick = useCallback(
    (type: 'dag' | 'upload') => {
      if (type === 'dag') trackFlowStart('HP-1');
      if (type === 'upload') trackFlowStart('HP-3');
      setSourceType(type);
      if (currentProjectId) {
        setProjectSourceType(currentProjectId, type);
      }
    },
    [currentProjectId, setProjectSourceType, setSourceType],
  );

  if (!sourceType) {
    return (
      <div data-tour="source-chooser" className="flex h-full items-center justify-center p-8">
        <SourceChooser onPick={handlePick} />
      </div>
    );
  }

  if (sourceType === 'upload') {
    return (
      <div className="h-full overflow-auto p-6">
        <UploadWizard />
      </div>
    );
  }

  return <DAGSourceView />;
};

const DAGSourceView = () => {
  useAutoValidation();

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-gray-200 bg-white px-4 py-2">
        <ValidationChips />
      </div>
      <div className="flex-1">
        <DAGCanvas />
      </div>
    </div>
  );
};
