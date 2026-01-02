import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// API functions
export const api = {
  // Applications
  createApplication: async (data: { application_ref: string; applicant_name?: string }) => {
    const response = await apiClient.post('/api/v1/applications', data);
    return response.data;
  },

  getApplications: async (page = 1, pageSize = 20) => {
    const response = await apiClient.get('/api/v1/applications', {
      params: { skip: (page - 1) * pageSize, limit: pageSize },
    });
    return response.data;
  },

  // File upload
  uploadFiles: async (
    applicationRef: string,
    files: File[],
    onProgress?: (progress: number) => void
  ) => {
    // Upload files one at a time since backend accepts single file per request
    const results = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post(`/api/v1/applications/${applicationRef}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            const fileProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            const totalProgress = Math.round(((i + (fileProgress / 100)) / files.length) * 100);
            onProgress(totalProgress);
          }
        },
      });
      results.push(response.data);
    }
    
    // Return the last result (or first if you prefer)
    return results[results.length - 1] || { run_id: null };
  },

  // Runs
  getRuns: async (page = 1, pageSize = 20, status?: string) => {
    const response = await apiClient.get('/api/v1/runs', {
      params: { skip: (page - 1) * pageSize, limit: pageSize, status },
    });
    return response.data;
  },

  getRunById: async (runId: number) => {
    const response = await apiClient.get(`/api/v1/runs/${runId}`);
    return response.data;
  },

  // Results
  getRunResults: async (runId: number) => {
    const response = await apiClient.get(`/api/v1/runs/${runId}/results`);
    return response.data;
  },

  // Validation checks
  getValidationChecks: async (submissionId: number) => {
    const response = await apiClient.get(`/api/v1/submissions/${submissionId}/checks`);
    return response.data;
  },
};
