import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes timeout for file uploads
  timeoutErrorMessage: 'Request timeout - file upload took too long',
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
    // Enhanced error handling
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      error.message = 'Upload timeout - please try again with a smaller file or check your connection';
    }

    if (error.code === 'ERR_NETWORK') {
      error.message = 'Network error - cannot connect to backend server';
    }

    if (error.response?.status === 401) {
      // Only redirect to login if auth is actually configured
      const hasToken = localStorage.getItem('token');
      if (hasToken) {
        localStorage.removeItem('token');
        // Note: Login page doesn't exist yet, so just clear token for now
        console.warn('Authentication failed - token cleared');
      }
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

  getApplicationDetails: async (applicationId: number) => {
    const response = await apiClient.get(`/api/v1/applications/id/${applicationId}`);
    return response.data;
  },

  // File upload
  uploadFiles: async (
    applicationRef: string,
    files: File[],
    onProgress?: (progress: number) => void,
    applicationType?: string
  ) => {
    // Upload files one at a time since backend accepts single file per request
    const results = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);
      if (applicationType) {
        formData.append('application_type', applicationType);
      }

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

  uploadApplicationRun: async (
    applicationId: number,
    files: File[],
    onProgress?: (progress: number) => void,
    applicationType?: string
  ) => {
    const results = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);
      if (applicationType) {
        formData.append('application_type', applicationType);
      }

      const response = await apiClient.post(`/api/v1/applications/${applicationId}/runs`, formData, {
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

  compareRuns: async (runIdA: number, runIdB: number) => {
    const response = await apiClient.get('/api/v1/runs/compare', {
      params: { run_id_a: runIdA, run_id_b: runIdB },
    });
    return response.data;
  },

  // Validation checks
  getValidationChecks: async (submissionId: number) => {
    const response = await apiClient.get(`/api/v1/submissions/${submissionId}/checks`);
    return response.data;
  },

  // HIL Review
  getUserInfo: async () => {
    // Extract user info from JWT token
    const token = localStorage.getItem('token');
    if (!token) {
      return { user_id: null, role: 'guest', auth_type: 'none' };
    }
    
    try {
      // Decode JWT payload (middle part)
      const payload = JSON.parse(atob(token.split('.')[1]));
      return {
        user_id: payload.sub || payload.user_id || null,
        role: payload.role || 'guest',
        auth_type: payload.auth_type || 'jwt',
      };
    } catch (err) {
      console.error('Failed to decode token:', err);
      return { user_id: null, role: 'guest', auth_type: 'none' };
    }
  },

  checkUserRole: async (allowedRoles: string[]) => {
    try {
      const response = await apiClient.get('/api/v1/auth/user-info');
      const userInfo = response.data;
      return allowedRoles.includes(userInfo.role);
    } catch (err) {
      console.error('Failed to check user role:', err);
      // Fallback to local token check
      const userInfo = await api.getUserInfo();
      return allowedRoles.includes(userInfo.role);
    }
  },

  submitReviewDecision: async (runId: number, checkId: number, decision: string, comment?: string) => {
    const response = await apiClient.post(`/api/v1/runs/${runId}/findings/${checkId}/review`, {
      decision,
      comment: comment || '',
    });
    return response.data;
  },

  submitEvidenceFeedback: async (
    runId: number,
    checkId: number,
    payload: {
      document_id: number;
      page_number?: number;
      evidence_id?: number;
      is_relevant: boolean;
      comment?: string;
    }
  ) => {
    const response = await apiClient.post(`/api/v1/runs/${runId}/findings/${checkId}/evidence-feedback`, payload);
    return response.data;
  },

  downloadReviewReport: async (runId: number) => {
    const response = await apiClient.get(`/api/v1/runs/${runId}/review-report`, {
      responseType: 'blob',
    });
    return response.data;
  },

  getReviewStatus: async (runId: number) => {
    const response = await apiClient.get(`/api/v1/runs/${runId}/review-status`);
    return response.data;
  },

  completeReview: async (runId: number) => {
    const response = await apiClient.post(`/api/v1/runs/${runId}/complete-review`);
    return response.data;
  },

  reclassifyDocument: async (runId: number, documentId: number, newType: string) => {
    const response = await apiClient.post(`/api/v1/runs/${runId}/reclassify_document`, {
      document_id: documentId,
      document_type: newType,
    });
    return response.data;
  },

  // BNG Decision
  submitBNGDecision: async (runId: number, bngApplicable: boolean, exemptionReason?: string) => {
    const response = await apiClient.post(`/api/v1/runs/${runId}/bng-decision`, {
      bng_applicable: bngApplicable,
      exemption_reason: exemptionReason,
    });
    return response.data;
  },

  // Authentication
  login: async (username: string, password: string) => {
    const response = await apiClient.post('/api/v1/auth/login', {
      username,
      password,
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/api/v1/auth/me');
    return response.data;
  },

  refreshToken: async () => {
    const response = await apiClient.post('/api/v1/auth/refresh');
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/api/v1/auth/logout');
    return response.data;
  },
};
