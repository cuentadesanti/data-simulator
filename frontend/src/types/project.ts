import type { DAGDefinition } from './dag';

// Project and Version types for project management

export interface ProjectVersion {
  id: string;
  version_number: number;
  created_at: string;
  is_current: boolean;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  current_version: ProjectVersion | null;
  versions?: ProjectVersion[];
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  dag_definition?: DAGDefinition; // Initial DAG definition
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

export interface CreateVersionRequest {
  dag_definition: DAGDefinition; // DAG definition
}
