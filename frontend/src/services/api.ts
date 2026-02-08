import axios from 'axios';
import type { AxiosInstance, AxiosError } from 'axios';
import type { DAGDefinition, ValidationError } from '../types/dag';
import type {
  Project,
  ProjectVersion,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateVersionRequest,
  UpdateVersionRequest,
} from '../types/project';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token provider for auth
let getToken: (() => Promise<string | null>) | null = null;

export const setTokenProvider = (provider: () => Promise<string | null>) => {
  getToken = provider;
};

// Request interceptor for auth
api.interceptors.request.use(async (config) => {
  if (getToken) {
    try {
      const token = await getToken();
      if (token) {
        // Use bracket notation to ensure compatibility with all axios versions/types
        config.headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Failed to get auth token', error);
    }
  }
  return config;
});

// Error handling
export class APIError extends Error {
  code: string;
  details?: Record<string, unknown>;
  nodeId?: string;

  constructor(message: string, code: string, details?: Record<string, unknown>, nodeId?: string) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.details = details;
    this.nodeId = nodeId;
  }
}

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (
    error: AxiosError<{
      error?: {
        code: string;
        message: string;
        details?: Record<string, unknown>;
        node_id?: string;
      };
    }>
  ) => {
    if (error.response?.data?.error) {
      const { code, message, details, node_id } = error.response.data.error;
      throw new APIError(message, code, details, node_id);
    }
    throw new APIError(error.message || 'An unexpected error occurred', 'UNKNOWN_ERROR');
  }
);

// Types for API responses
export interface DistributionParam {
  name: string;
  description: string;
  type: 'float' | 'int' | 'list' | 'dict';
  required: boolean;
  default?: number | string | boolean | number[] | string[];
  min_value?: number;
  max_value?: number;
}

export interface DistributionInfo {
  name: string;
  display_name: string;
  category: 'continuous' | 'discrete' | 'categorical';
  description: string;
  parameters: DistributionParam[];
  default_dtype: 'float' | 'int' | 'category' | 'bool';
}

export type EdgeStatus = 'used' | 'unused' | 'invalid';

export interface EdgeValidation {
  source: string;
  target: string;
  status: EdgeStatus;
  reason?: string;
}

export interface MissingEdge {
  source: string;
  target: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  structured_errors: ValidationError[];
  topological_order?: string[];
  edge_statuses: EdgeValidation[];
  missing_edges: MissingEdge[];
  sanitized_dag?: DAGDefinition;
}

export interface PreviewResult {
  data: Record<string, unknown>[];
  columns: string[];
  rows: number;
  seed: number;
  warnings: string[];
  sanitized_dag?: DAGDefinition;
}

export interface GenerationResult {
  job_id?: string;
  status: 'completed' | 'pending' | 'running' | 'failed';
  rows: number;
  columns: string[];
  seed: number;
  format: 'csv' | 'parquet' | 'json';
  size_bytes?: number;
  schema_version: string;
  warnings: string[];
  download_url?: string;
}

// API functions
export const distributionsApi = {
  /**
   * Get all common/curated distributions
   */
  getAll: async (): Promise<DistributionInfo[]> => {
    const response = await api.get<{ distributions: DistributionInfo[] }>('/api/distributions');
    return response.data.distributions;
  },

  /**
   * Search scipy distributions by query
   */
  search: async (query: string, limit = 10): Promise<DistributionInfo[]> => {
    const response = await api.get<{ results: DistributionInfo[]; query: string }>(
      '/api/distributions/search',
      { params: { q: query, limit } }
    );
    return response.data.results;
  },
};

export const dagApi = {
  /**
   * Validate a DAG definition
   */
  validate: async (dag: DAGDefinition): Promise<ValidationResult> => {
    const response = await api.post<ValidationResult>('/api/dag/validate', dag);
    return response.data;
  },

  /**
   * Generate preview data (small sample)
   */
  preview: async (dag: DAGDefinition): Promise<PreviewResult> => {
    const response = await api.post<PreviewResult>('/api/dag/preview', dag);
    return response.data;
  },

  /**
   * Generate full dataset
   */
  generate: async (
    dag: DAGDefinition,
    format: 'csv' | 'parquet' | 'json' = 'csv'
  ): Promise<Blob> => {
    // For CSV/Parquet, always get as blob
    // For JSON format, the response is still binary (JSON string)
    const response = await api.post('/api/dag/generate', dag, {
      params: { format },
      responseType: 'blob',
    });

    return response.data as Blob;
  },

  /**
   * Download generated file (for async jobs)
   */
  download: async (jobId: string): Promise<Blob> => {
    const response = await api.get(`/api/jobs/${jobId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const jobsApi = {
  /**
   * Get job status
   */
  getStatus: async (jobId: string): Promise<GenerationResult> => {
    const response = await api.get<GenerationResult>(`/api/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Poll job until complete
   */
  pollUntilComplete: async (
    jobId: string,
    onProgress?: (result: GenerationResult) => void,
    intervalMs = 1000,
    maxAttempts = 600 // 10 minutes
  ): Promise<GenerationResult> => {
    let attempts = 0;
    while (attempts < maxAttempts) {
      const result = await jobsApi.getStatus(jobId);
      onProgress?.(result);

      if (result.status === 'completed' || result.status === 'failed') {
        return result;
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
      attempts++;
    }

    throw new APIError('Job polling timeout', 'TIMEOUT_ERROR');
  },
};

// Helper to download blob as file
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

// Projects API with DAG data
export interface ProjectWithDAG extends Project {
  current_dag: DAGDefinition | null;
}

export interface VersionWithDAG extends ProjectVersion {
  dag_definition: DAGDefinition | null;
}

export interface ShareVersionResponse {
  project_id: string;
  version_id: string;
  is_public: boolean;
  share_token: string | null;
  public_path: string | null;
}

export interface PublicDAGResponse {
  project_id: string;
  project_name: string;
  version_id: string;
  version_number: number;
  shared_at: string;
  dag_definition: DAGDefinition;
}

export const projectsApi = {
  /**
   * List all projects
   */
  list: async (): Promise<Project[]> => {
    const response = await api.get<{ projects: Project[] }>('/api/projects');
    return response.data.projects;
  },

  /**
   * Get a project by ID (includes current version's DAG)
   */
  get: async (id: string): Promise<ProjectWithDAG> => {
    const response = await api.get<ProjectWithDAG>(`/api/projects/${id}`);
    return response.data;
  },

  /**
   * Create a new project
   */
  create: async (data: CreateProjectRequest): Promise<Project> => {
    const response = await api.post<Project>('/api/projects', data);
    return response.data;
  },

  /**
   * Update a project
   */
  update: async (id: string, data: UpdateProjectRequest): Promise<Project> => {
    const response = await api.put<Project>(`/api/projects/${id}`, data);
    return response.data;
  },

  /**
   * Delete a project
   */
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/projects/${id}`);
  },

  /**
   * List versions for a project
   */
  listVersions: async (projectId: string): Promise<ProjectVersion[]> => {
    const response = await api.get<{ versions: ProjectVersion[] }>(
      `/api/projects/${projectId}/versions`
    );
    return response.data.versions;
  },

  /**
   * Create a new version for a project
   */
  createVersion: async (
    projectId: string,
    data: CreateVersionRequest
  ): Promise<ProjectVersion> => {
    const response = await api.post<ProjectVersion>(`/api/projects/${projectId}/versions`, data);
    return response.data;
  },

  /**
   * Update a DAG version in place
   */
  updateVersion: async (
    projectId: string,
    versionId: string,
    data: UpdateVersionRequest
  ): Promise<ProjectVersion> => {
    const response = await api.put<ProjectVersion>(
      `/api/projects/${projectId}/versions/${versionId}`,
      data
    );
    return response.data;
  },

  /**
   * Get a specific version with its DAG
   */
  getVersion: async (projectId: string, versionId: string): Promise<VersionWithDAG> => {
    const response = await api.get<VersionWithDAG>(
      `/api/projects/${projectId}/versions/${versionId}`
    );
    return response.data;
  },

  /**
   * Set a version as current
   */
  setCurrentVersion: async (projectId: string, versionId: string): Promise<void> => {
    await api.post(`/api/projects/${projectId}/versions/${versionId}/set-current`);
  },

  /**
   * Enable public sharing for a version.
   */
  shareVersion: async (
    projectId: string,
    versionId: string
  ): Promise<ShareVersionResponse> => {
    const response = await api.post<ShareVersionResponse>(
      `/api/projects/${projectId}/versions/${versionId}/share`
    );
    return response.data;
  },

  /**
   * Disable public sharing for a version.
   */
  unshareVersion: async (
    projectId: string,
    versionId: string
  ): Promise<ShareVersionResponse> => {
    const response = await api.delete<ShareVersionResponse>(
      `/api/projects/${projectId}/versions/${versionId}/share`
    );
    return response.data;
  },
};

export const publicApi = {
  /**
   * Fetch a shared DAG by public token.
   */
  getSharedDAG: async (shareToken: string): Promise<PublicDAGResponse> => {
    const response = await api.get<PublicDAGResponse>(`/api/public/dags/${shareToken}`);
    return response.data;
  },
};

export default api;
