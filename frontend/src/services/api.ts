/**
 * API client for the data cleaning platform
 * Uses Axios for HTTP requests with error handling
 */

import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import type {
  Dataset,
  Job,
  DatasetMetrics,
  InteractiveSession,
  SuggestedAction,
  ApiResponse,
  PaginatedResponse,
  UploadResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const errorMessage = this.handleError(error);
        console.error('API Error:', errorMessage);
        return Promise.reject(new Error(errorMessage));
      }
    );
  }

  private handleError(error: AxiosError): string {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as { message?: string; error?: string };

      switch (status) {
        case 400:
          return data.message || 'Bad request. Please check your input.';
        case 401:
          return 'Authentication failed. Please log in again.';
        case 403:
          return 'You do not have permission to perform this action.';
        case 404:
          return data.message || 'Resource not found.';
        case 409:
          return data.message || 'Conflict. Resource may already exist.';
        case 422:
          return data.message || 'Validation failed. Please check your input.';
        case 500:
          return 'Server error. Please try again later.';
        default:
          return data.message || `Request failed with status ${status}`;
      }
    } else if (error.request) {
      return 'Network error. Please check your connection.';
    } else {
      return error.message || 'An unexpected error occurred.';
    }
  }

  // Dataset APIs
  async uploadDataset(file: File, taskName: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('task_name', taskName);

    const response = await this.client.post<UploadResponse>('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getDataset(id: string): Promise<Dataset> {
    const response = await this.client.get<Dataset>(`/datasets/${id}`);
    return response.data;
  }

  async getDatasets(page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<Dataset>> {
    const response = await this.client.get<PaginatedResponse<Dataset>>('/datasets', {
      params: { page, pageSize },
    });
    return response.data;
  }

  // Job APIs
  async startJob(datasetId: string): Promise<Job> {
    const response = await this.client.post<Job>('/jobs/batch', { dataset_id: datasetId, cleaning_mode: 'conservative' });
    return response.data;
  }

  async getJobStatus(jobId: string): Promise<Job> {
    const response = await this.client.get<Job>(`/jobs/${jobId}`);
    return response.data;
  }

  async getJobs(page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<Job>> {
    const response = await this.client.get<PaginatedResponse<Job>>('/jobs', {
      params: { page, pageSize },
    });
    return response.data;
  }

  // Metrics APIs
  async getMetrics(datasetId: string): Promise<DatasetMetrics> {
    const response = await this.client.get<DatasetMetrics>(`/metrics/${datasetId}`);
    return response.data;
  }

  // Interactive cleaning APIs
  async startInteractiveSession(datasetId: string): Promise<InteractiveSession> {
    const response = await this.client.post<InteractiveSession>(`/interactive/${datasetId}`);
    return response.data;
  }

  async getSuggestions(jobId: string): Promise<SuggestedAction[]> {
    const response = await this.client.get<SuggestedAction[]>(`/interactive/${jobId}/suggestions`);
    return response.data;
  }

  async applyAction(jobId: string, action: SuggestedAction): Promise<void> {
    await this.client.post(`/interactive/${jobId}/actions`, action);
  }

  async skipRow(jobId: string): Promise<void> {
    await this.client.post(`/interactive/${jobId}/skip`);
  }

  // Audit log
  async getAuditLog(jobId: string): Promise<ApiResponse<unknown>> {
    const response = await this.client.get<ApiResponse<unknown>>(`/jobs/${jobId}/audit`);
    return response.data;
  }

  // Keep-alive ping (prevents Render free-tier spin-down during user sessions)
  async keepAlive(): Promise<boolean> {
    try {
      const response = await this.client.get('/health', { timeout: 5000 });
      return response.status === 200;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export individual functions for convenience
export const uploadDataset = (file: File, taskName: string) => api.uploadDataset(file, taskName);
export const getDataset = (id: string) => api.getDataset(id);
export const getDatasets = (page?: number, pageSize?: number) => api.getDatasets(page, pageSize);
export const startJob = (datasetId: string) => api.startJob(datasetId);
export const getJobStatus = (jobId: string) => api.getJobStatus(jobId);
export const getJobs = (page?: number, pageSize?: number) => api.getJobs(page, pageSize);
export const getMetrics = (datasetId: string) => api.getMetrics(datasetId);
export const startInteractiveSession = (datasetId: string) => api.startInteractiveSession(datasetId);
export const getSuggestions = (jobId: string) => api.getSuggestions(jobId);
export const applyAction = (jobId: string, action: SuggestedAction) => api.applyAction(jobId, action);
export const skipRow = (jobId: string) => api.skipRow(jobId);
export const getAuditLog = (jobId: string) => api.getAuditLog(jobId);
export const keepAlive = () => api.keepAlive();
