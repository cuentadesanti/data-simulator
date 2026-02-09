import api from '../services/api';

export interface SourceMetadata {
  id: string;
  project_id: string;
  filename: string;
  format: string;
  size_bytes: number;
  schema: Array<{ name: string; dtype: string }>;
  upload_fingerprint: string;
  created_by: string;
  created_at: string;
}

export interface UploadSourceResponse {
  source_id: string;
  schema: Array<{ name: string; dtype: string }>;
  row_count_sample: number;
  warnings: string[];
}

export const sourcesApi = {
  upload: async (projectId: string, file: File): Promise<UploadSourceResponse> => {
    const form = new FormData();
    form.append('project_id', projectId);
    form.append('file', file);

    const response = await api.post<UploadSourceResponse>('/api/sources/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  get: async (sourceId: string): Promise<SourceMetadata> => {
    const response = await api.get<SourceMetadata>(`/api/sources/${sourceId}`);
    return response.data;
  },

  list: async (projectId: string): Promise<SourceMetadata[]> => {
    const response = await api.get<{ sources: SourceMetadata[] }>(`/api/sources?project_id=${projectId}`);
    return response.data.sources;
  },

  delete: async (sourceId: string): Promise<void> => {
    await api.delete(`/api/sources/${sourceId}`);
  },
};
