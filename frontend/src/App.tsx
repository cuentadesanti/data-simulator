import { useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { NodeEditor } from './components/Panel';
import { Toolbar } from './components/Toolbar';
import { MainTabs } from './components/MainTabs';
import { ToastProvider } from './components/common';
import { ProjectSidebar } from './components/ProjectSidebar';
import { useProjectStore, selectHasUnsavedChanges } from './stores/projectStore';
import { useDAGStore, selectActiveMainTab } from './stores/dagStore';

import '@xyflow/react/dist/style.css';

function App() {
  const hasUnsavedChanges = useProjectStore(selectHasUnsavedChanges);
  const activeTab = useDAGStore(selectActiveMainTab);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  return (
    <ToastProvider>
      <ReactFlowProvider>
        <div className="h-screen w-full flex flex-col bg-gray-50">
          {/* Top Toolbar */}
          <header className="flex-shrink-0 border-b border-gray-200 bg-white">
            <Toolbar />
          </header>

          {/* Main Content Area */}
          <div className="flex-1 flex overflow-hidden">
            {/* Project Sidebar (left) */}
            <ProjectSidebar />

            {/* Main Content with Tabs (DAG Canvas / Data Preview) */}
            <main className="flex-1 flex flex-col overflow-hidden">
              <MainTabs />
            </main>

            {/* Node Editor Panel (right) - only show on DAG tab */}
            {activeTab === 'dag' && (
              <aside className="w-96 flex-shrink-0 border-l border-gray-200 bg-white overflow-y-auto">
                <NodeEditor />
              </aside>
            )}
          </div>
        </div>
      </ReactFlowProvider>
    </ToastProvider>
  );
}

export default App;
