import type { ReactNode } from 'react';
import { Database, FlaskConical, Brain, Send } from 'lucide-react';
import { useWorkspaceStore, type Stage } from '../../stores/workspaceStore';

interface StageItem {
  id: Stage;
  label: string;
  icon: ReactNode;
}

const stages: StageItem[] = [
  { id: 'source', label: 'Source', icon: <Database size={16} /> },
  { id: 'transform', label: 'Transform', icon: <FlaskConical size={16} /> },
  { id: 'model', label: 'Model', icon: <Brain size={16} /> },
  { id: 'publish', label: 'Publish', icon: <Send size={16} /> },
];

export const StageNav = () => {
  const activeStage = useWorkspaceStore((state) => state.activeStage);
  const setActiveStage = useWorkspaceStore((state) => state.setActiveStage);

  return (
    <nav data-tour="stage-nav" className="flex flex-col gap-1">
      {stages.map((stage) => {
        const isActive = activeStage === stage.id;
        return (
          <button
            key={stage.id}
            type="button"
            onClick={() => setActiveStage(stage.id)}
            className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            }`}
          >
            {stage.icon}
            <span>{stage.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
