export interface Application {
  id: number;
  application_ref: string;
  applicant_name?: string;
  created_at: string;
}

export interface Run {
  id: number;
  run_type: string;
  application_id?: number;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed';
  error_message?: string;
  run_metadata?: Record<string, any>;
}

export interface ValidationCheck {
  id: number;
  submission_id: number;
  rule_id: string;
  status: 'pass' | 'fail' | 'needs_review';
  severity: 'blocker' | 'critical' | 'warning' | 'info';
  message: string;
  details?: Record<string, any>;
  created_at: string;
}

export interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'uploading' | 'completed' | 'error';
  error?: string;
}
