import { useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { NodeEditor } from './components/Panel';
import { Toolbar } from './components/Toolbar';
import { MainTabs } from './components/MainTabs';
import { ToastProvider } from './components/common';
import { ProjectSidebar } from './components/ProjectSidebar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { useProjectStore, selectHasUnsavedChanges } from './stores/projectStore';
import { useDAGStore, selectActiveMainTab } from './stores/dagStore';

import {
  useAuth,
  SignedIn,
  SignedOut,
  RedirectToSignIn,
} from '@clerk/clerk-react';
import { setTokenProvider } from './services/api';
import '@xyflow/react/dist/style.css';

function App() {
  const hasUnsavedChanges = useProjectStore(selectHasUnsavedChanges);
  const activeTab = useDAGStore(selectActiveMainTab);
  const { getToken } = useAuth();

  // Initialize auth token provider
  useEffect(() => {
    setTokenProvider(getToken);
  }, [getToken]);

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
        <SignedIn>
          <div className="h-screen w-full flex flex-col bg-gray-50">
            {/* Top Toolbar */}
            <header className="flex-shrink-0 border-b border-gray-200 bg-white">
              <ErrorBoundary name="Toolbar">
                <Toolbar />
              </ErrorBoundary>
            </header>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
              {/* Project Sidebar (left) */}
              <ErrorBoundary name="Project Sidebar">
                <ProjectSidebar />
              </ErrorBoundary>

              {/* Main Content with Tabs (DAG Canvas / Data Preview) */}
              <main className="flex-1 flex flex-col overflow-hidden">
                <ErrorBoundary name="Main Content">
                  <MainTabs />
                </ErrorBoundary>
              </main>

              {/* Node Editor Panel (right) - only show on DAG tab */}
              {activeTab === 'dag' && (
                <aside className="w-96 flex-shrink-0 border-l border-gray-200 bg-white overflow-y-auto">
                  <ErrorBoundary name="Node Editor">
                    <NodeEditor />
                  </ErrorBoundary>
                </aside>
              )}
            </div>
          </div>
        </SignedIn>
        <SignedOut>
          <RedirectToSignIn />
        </SignedOut>
      </ReactFlowProvider>
    </ToastProvider>
  );
}

export default App;

