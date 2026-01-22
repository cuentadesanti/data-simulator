import { LayoutGrid, Table2, GitBranch } from 'lucide-react';
import { DAGCanvas } from '../Canvas';
import { DataView } from './DataView';
import { PipelineView } from './PipelineView';
import { useDAGStore, selectPreviewData, selectActiveMainTab } from '../../stores/dagStore';
import { usePipelineStore, selectCurrentPipelineId, selectPipelineSteps } from '../../stores/pipelineStore';

type TabId = 'dag' | 'data' | 'pipeline';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const tabs: Tab[] = [
  {
    id: 'dag',
    label: 'DAG Canvas',
    icon: <LayoutGrid size={16} />,
  },
  {
    id: 'data',
    label: 'Data Preview',
    icon: <Table2 size={16} />,
  },
  {
    id: 'pipeline',
    label: 'Pipeline',
    icon: <GitBranch size={16} />,
  },
];

export const MainTabs = () => {
  const activeTab = useDAGStore(selectActiveMainTab);
  const setActiveTab = useDAGStore((s) => s.setActiveMainTab);
  const previewData = useDAGStore(selectPreviewData);
  const hasData = previewData && previewData.length > 0;

  const currentPipelineId = usePipelineStore(selectCurrentPipelineId);
  const pipelineSteps = usePipelineStore(selectPipelineSteps);
  const hasPipeline = !!currentPipelineId;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Tab Bar */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.icon}
              {tab.label}
              {tab.id === 'data' && hasData && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                  {previewData.length}
                </span>
              )}
              {tab.id === 'pipeline' && hasPipeline && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                  {pipelineSteps.length} steps
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'dag' && (
          <div className="w-full h-full">
            <DAGCanvas />
          </div>
        )}
        {activeTab === 'data' && (
          <div className="w-full h-full">
            <DataView />
          </div>
        )}
        {activeTab === 'pipeline' && (
          <div className="w-full h-full">
            <PipelineView />
          </div>
        )}
      </div>
    </div>
  );
};
