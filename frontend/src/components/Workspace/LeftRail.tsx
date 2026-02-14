import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { StageNav } from './StageNav';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useProjectStore, selectCurrentProject } from '../../stores/projectStore';

export const LeftRail = () => {
  const collapsed = useWorkspaceStore((state) => state.leftRailCollapsed);
  const setCollapsed = useWorkspaceStore((state) => state.setLeftRailCollapsed);
  const currentProject = useProjectStore(selectCurrentProject);
  const currentVersionId = useProjectStore((state) => state.currentVersionId);

  return (
    <aside
      className={`h-full border-r border-gray-200 bg-white transition-all ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-3">
        {!collapsed && (
          <div>
            <div className="text-sm font-semibold text-gray-900">Workspace</div>
            <div className="text-xs text-gray-500">
              {currentProject?.name ?? 'No project selected'}
            </div>
            <div className="text-xs text-gray-400">
              {currentProject?.current_version?.version_number
                ? `v${currentProject.current_version.version_number}`
                : currentVersionId
                  ? 'Version selected'
                  : 'No version'}
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="rounded p-1 text-gray-500 hover:bg-gray-100"
        >
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      <div className="space-y-3 p-2">{!collapsed && <StageNav />}</div>
    </aside>
  );
};
