import { useState } from 'react';
import { projectsApi } from '../services/api';
import { useToast } from '../components/common';
import {
  trackCompletionLatency,
  trackFeedbackLatencyOnNextPaint,
  trackFlowComplete,
} from '../services/telemetry';

export function useShareVersion() {
  const [isSharing, setIsSharing] = useState(false);
  const { addToast } = useToast();

  const shareVersion = async (projectId: string | null, versionId: string | null) => {
    if (!projectId || !versionId) {
      addToast('info', 'Save a project version before sharing');
      return null;
    }
    const started = performance.now();
    setIsSharing(true);
    trackFeedbackLatencyOnNextPaint('project.share', started, {
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      const share = await projectsApi.shareVersion(projectId, versionId);
      if (!share.share_token) {
        addToast('error', 'Failed to create share link');
        return null;
      }
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const shareUrl = `${apiBase}${share.public_path ?? `/api/public/dags/${share.share_token}`}`;
      trackFlowComplete('HP-2');
      trackCompletionLatency('project.share', started, { user_initiated: true });
      try {
        await navigator.clipboard.writeText(shareUrl);
        addToast('success', 'Share link copied');
      } catch {
        addToast('success', `Share link: ${shareUrl}`);
      }
      return shareUrl;
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Share failed');
      return null;
    } finally {
      setIsSharing(false);
    }
  };

  return { isSharing, shareVersion };
}
