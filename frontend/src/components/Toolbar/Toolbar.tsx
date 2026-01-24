import React, { useState } from 'react';
import { CheckCircle, Download, Upload, Trash2, Save } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import { useDAGStore, selectActiveMainTab } from '../../stores/dagStore';
import { useProjectStore } from '../../stores/projectStore';
import { dagApi, downloadBlob } from '../../services/api';
import { useToast } from '../common';
import { AddNodeDropdown } from './AddNodeDropdown';
import { GenerateButton } from './GenerateButton';
import { ValidationStatus } from './ValidationStatus';

import { NewProjectDialog } from '../ProjectSidebar/NewProjectDialog';

export const Toolbar: React.FC = () => {
  const [isValidating, setIsValidating] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isNewProjectDialogOpen, setIsNewProjectDialogOpen] = useState(false);
  const { addToast } = useToast();

  const {
    exportDAG,
    importDAG,
    clearDAG,
    setValidationErrors,
    setStructuredErrors,
    setPreviewData,
    setEdgeStatuses,
    setLastValidationResult,
  } = useDAGStore();

  const saveVersion = useProjectStore((s) => s.saveVersion);
  const isSaving = useProjectStore((s) => s.isSaving);
  const hasUnsavedChanges = useProjectStore((s) => s.hasUnsavedChanges);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);

  const activeMainTab = useDAGStore(selectActiveMainTab);
  const isDagTab = activeMainTab === 'dag';

  // Save version
  const handleSave = async () => {
    // If no project is selected, open the New Project dialog
    if (!currentProjectId) {
      setIsNewProjectDialogOpen(true);
      return;
    }

    try {
      await saveVersion();
      addToast('success', 'Project saved successfully');
    } catch (error) {
      addToast('error', 'Failed to save project');
      console.error(error);
    }
  };

  // Validate DAG
  const handleValidate = async () => {
    setIsValidating(true);
    setLastValidationResult('pending');
    try {
      const dag = exportDAG();
      const result = await dagApi.validate(dag);

      // Always update edge statuses from validation result
      setEdgeStatuses(result.edge_statuses || [], result.missing_edges || []);

      // If backend sanitized/migrated IDs, update local state
      if (result.sanitized_dag?.was_migrated) {
        importDAG(result.sanitized_dag);
      }

      if (result.valid) {
        setValidationErrors([]);
        setStructuredErrors([]);
        setLastValidationResult('valid');
        addToast('success', 'DAG is valid!');
      } else {
        setValidationErrors(result.errors);
        setStructuredErrors(result.structured_errors || []);
        setLastValidationResult('invalid');
        addToast('error', `Validation failed: ${result.errors.length} error(s)`);
      }
    } catch (error) {
      console.error('Validation error:', error);
      setEdgeStatuses([], []); // Clear edge statuses on error
      setLastValidationResult('invalid');
      addToast(
        'error',
        `Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsValidating(false);
    }
  };

  // Generate preview data
  const handlePreview = async () => {
    setIsPreviewing(true);
    try {
      const dag = exportDAG();
      const result = await dagApi.preview(dag);
      setPreviewData(result.data, result.columns);

      // If backend sanitized/migrated IDs, update local state
      if (result.sanitized_dag?.was_migrated) {
        importDAG(result.sanitized_dag);
      }

      addToast('success', `Preview generated: ${result.rows} rows`);
    } catch (error) {
      console.error('Preview error:', error);
      addToast(
        'error',
        `Preview failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsPreviewing(false);
    }
  };

  // Export DAG to JSON
  const handleExportJSON = () => {
    try {
      const dag = exportDAG();
      const json = JSON.stringify(dag, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      downloadBlob(blob, 'dag-definition.json');
      addToast('success', 'DAG exported successfully');
    } catch (error) {
      console.error('Export error:', error);
      addToast(
        'error',
        `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  // Import DAG from JSON
  const handleImportJSON = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const dag = JSON.parse(text);
        importDAG(dag);
        addToast('success', 'DAG imported successfully!');
      } catch (error) {
        console.error('Import error:', error);
        addToast(
          'error',
          `Import failed: ${error instanceof Error ? error.message : 'Invalid JSON file'}`
        );
      }
    };
    input.click();
  };

  // Clear DAG with confirmation
  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear the entire DAG? This cannot be undone.')) {
      clearDAG();
      addToast('info', 'DAG cleared');
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-2">
      <NewProjectDialog
        open={isNewProjectDialogOpen}
        onClose={() => setIsNewProjectDialogOpen(false)}
      />
      <div className="flex items-center gap-2">
        {/* DAG-specific controls - only show on DAG tab */}
        {isDagTab && (
          <>
            {/* Add Node Dropdown */}
            <AddNodeDropdown />

            {/* Divider */}
            <div className="h-6 w-px bg-gray-300" />

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={isSaving || (!!currentProjectId && !hasUnsavedChanges)}
              className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              title={
                !currentProjectId
                  ? 'Save as new project'
                  : !hasUnsavedChanges
                    ? 'No changes to save'
                    : 'Save current version'
              }
            >
              <Save size={16} />
              <span className="text-sm font-medium">{isSaving ? 'Saving...' : 'Save'}</span>
            </button>

            {/* Validate Button */}
            <button
              onClick={handleValidate}
              disabled={isValidating}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <CheckCircle size={16} />
              <span className="text-sm font-medium">
                {isValidating ? 'Validating...' : 'Validate'}
              </span>
            </button>
          </>
        )}

        {/* Generate (Split Button) replaces Preview */}
        <GenerateButton onGeneratePreview={handlePreview} isPreviewing={isPreviewing} />

        {/* Divider */}
        <div className="h-6 w-px bg-gray-300" />

        {/* Export JSON */}
        <button
          onClick={handleExportJSON}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
        >
          <Download size={16} />
          <span className="text-sm font-medium">Export JSON</span>
        </button>

        {/* Import JSON */}
        <button
          onClick={handleImportJSON}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
        >
          <Upload size={16} />
          <span className="text-sm font-medium">Import JSON</span>
        </button>

        {/* Clear Button */}
        <button
          onClick={handleClear}
          className="flex items-center gap-2 px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
        >
          <Trash2 size={16} />
          <span className="text-sm font-medium">Clear</span>
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Validation Status */}
        <ValidationStatus />

        {/* Auth */}
        <div className="ml-2 pl-2 border-l border-gray-200 flex items-center">
          <SignedOut>
            <SignInButton mode="modal">
              <button className="px-3 py-1.5 bg-gray-900 text-white text-sm font-medium rounded hover:bg-gray-800 transition-colors">
                Sign In
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton />
          </SignedIn>
        </div>
      </div>
    </div>
  );
};
