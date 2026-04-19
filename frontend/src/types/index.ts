/**
 * TypeScript type definitions for the data cleaning platform
 */

// Dataset types
export interface Dataset {
  id: string;
  name: string;
  filename: string;
  size: number;
  rows: number;
  columns: number;
  taskType: 'easy' | 'medium' | 'hard';
  uploadedAt: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
}

export interface DatasetUploadRequest {
  file: File;
  taskName: string;
}

// Job types
export interface Job {
  id: string;
  datasetId: string;
  datasetName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  actions: CleaningAction[];
}

export interface CleaningAction {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  confidence: number;
  before: unknown;
  after: unknown;
}

// Metrics types
export interface DatasetMetrics {
  datasetId: string;
  totalRows: number;
  cleanedRows: number;
  issuesFound: number;
  issuesFixed: number;
  accuracy: number;
  cleaningDuration: number;
  actionsBreakdown: Record<string, number>;
}

// Interactive cleaning types
export interface RowData {
  id: string | number;
  [key: string]: unknown;
}

export interface SuggestedAction {
  action: string;
  confidence: number;
  description: string;
  reason: string;
}

export interface InteractiveSession {
  jobId: string;
  currentRow: RowData;
  suggestions: SuggestedAction[];
  history: CleaningAction[];
}

// Dashboard types
export interface DashboardStats {
  totalJobs: number;
  completedJobs: number;
  avgAccuracy: number;
  totalRowsCleaned: number;
  recentJobs: Job[];
}

// API response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}
