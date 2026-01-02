import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  Typography,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  CircularProgress,
  AlertTitle,
  Tooltip,
} from '@mui/material';
import { CloudUpload, Close, CheckCircle, Error as ErrorIcon, Refresh } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errorUtils';

interface FileProgress {
  fileName: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  size: number;
}

const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200MB in bytes
const APP_REF_PATTERN = /^[A-Z0-9\-\/]+$/i; // Allow alphanumeric, hyphens, slashes

export default function NewApplication() {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as {
    applicationId?: number;
    applicationRef?: string;
    applicantName?: string;
  } | null;
  const existingApplicationId = locationState?.applicationId ?? null;
  const isVersionUpload = Boolean(existingApplicationId);
  const [applicationRef, setApplicationRef] = useState('');
  const [applicantName, setApplicantName] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [fileProgress, setFileProgress] = useState<Map<string, FileProgress>>(new Map());
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [lastRunId, setLastRunId] = useState<number | null>(null);
  const [createdApplicationId, setCreatedApplicationId] = useState<number | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);
  const [loadingApplication, setLoadingApplication] = useState(false);

  // Check backend health function
  const checkBackendHealth = async () => {
    try {
      await fetch('http://localhost:8000/api/v1/health');
      setBackendAvailable(true);
    } catch (err) {
      setBackendAvailable(false);
      setError('Backend server is not running. Please start the backend server.');
    }
  };

  // Check backend health on component mount
  useEffect(() => {
    checkBackendHealth();
  }, []);

  useEffect(() => {
    const loadExistingApplication = async () => {
      if (!existingApplicationId) {
        if (locationState?.applicationRef) {
          setApplicationRef(locationState.applicationRef);
        }
        if (locationState?.applicantName) {
          setApplicantName(locationState.applicantName);
        }
        return;
      }

      if (locationState?.applicationRef) {
        setApplicationRef(locationState.applicationRef);
      }
      if (locationState?.applicantName) {
        setApplicantName(locationState.applicantName);
      }

      if (locationState?.applicationRef && locationState?.applicantName) {
        return;
      }

      setLoadingApplication(true);
      try {
        const details = await api.getApplicationDetails(existingApplicationId);
        setApplicationRef(details.reference_number || '');
        setApplicantName(details.applicant_name || '');
      } catch (err: any) {
        console.error('Failed to load application for version upload:', err);
        setError(getApiErrorMessage(err, 'Failed to load application details for version upload'));
      } finally {
        setLoadingApplication(false);
      }
    };

    loadExistingApplication();
  }, [existingApplicationId, locationState?.applicationRef, locationState?.applicantName]);

  const validateFiles = (newFiles: File[]): string[] => {
    const errors: string[] = [];
    const existingNames = new Set(files.map(f => f.name));

    newFiles.forEach((file) => {
      // Check file extension
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        errors.push(`${file.name}: Only PDF files are allowed`);
      }

      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: File size ${(file.size / 1024 / 1024).toFixed(2)}MB exceeds limit of 200MB`);
      }

      // Check for 0-byte files
      if (file.size === 0) {
        errors.push(`${file.name}: File is empty (0 bytes)`);
      }

      // Check for duplicates
      if (existingNames.has(file.name)) {
        errors.push(`${file.name}: File already added`);
      }
    });

    return errors;
  };

  const validateApplicationRef = (ref: string): string[] => {
    const errors: string[] = [];

    if (!ref.trim()) {
      errors.push('Application reference is required');
      return errors;
    }

    if (ref.trim().length < 3) {
      errors.push('Application reference must be at least 3 characters');
    }

    if (!APP_REF_PATTERN.test(ref.trim())) {
      errors.push('Application reference can only contain letters, numbers, hyphens, and slashes');
    }

    return errors;
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: MAX_FILE_SIZE,
    onDrop: (acceptedFiles, rejectedFiles) => {
      const errors = validateFiles(acceptedFiles);

      // Handle rejected files
      rejectedFiles.forEach((rejection) => {
        if (rejection.errors.some(e => e.code === 'file-too-large')) {
          errors.push(`${rejection.file.name}: File is too large (max 200MB)`);
        }
        if (rejection.errors.some(e => e.code === 'file-invalid-type')) {
          errors.push(`${rejection.file.name}: Invalid file type (PDF only)`);
        }
      });

      if (errors.length > 0) {
        setValidationErrors(errors);
      } else {
        setFiles((prev) => [...prev, ...acceptedFiles]);
        setValidationErrors([]);
        setError('');
      }
    },
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setValidationErrors([]);
  };

  const retryFile = async (fileName: string) => {
    const fileToRetry = files.find(f => f.name === fileName);
    if (!fileToRetry) return;

    const progress = new Map(fileProgress);
    progress.set(fileName, {
      fileName,
      progress: 0,
      status: 'uploading',
      size: fileToRetry.size,
    });
    setFileProgress(progress);

    try {
      const uploadHandler = isVersionUpload && existingApplicationId
        ? api.uploadApplicationRun.bind(null, existingApplicationId)
        : api.uploadFiles.bind(null, applicationRef.trim());

      await uploadHandler([fileToRetry], (uploadProgress: number) => {
        const updated = new Map(fileProgress);
        updated.set(fileName, {
          fileName,
          progress: uploadProgress,
          status: 'uploading',
          size: fileToRetry.size,
        });
        setFileProgress(updated);
      });

      const updated = new Map(fileProgress);
      updated.set(fileName, {
        fileName,
        progress: 100,
        status: 'completed',
        size: fileToRetry.size,
      });
      setFileProgress(updated);
    } catch (err: any) {
      const updated = new Map(fileProgress);
      updated.set(fileName, {
        fileName,
        progress: 0,
        status: 'error',
        error: err.response?.data?.detail || err.message || 'Upload failed',
        size: fileToRetry.size,
      });
      setFileProgress(updated);
    }
  };

  const handleSubmit = async () => {
    // Validate application reference
    if (!isVersionUpload) {
      const refErrors = validateApplicationRef(applicationRef);
      if (refErrors.length > 0) {
        setValidationErrors(refErrors);
        return;
      }
    }

    if (isVersionUpload && !existingApplicationId) {
      setValidationErrors(['Select an existing case before uploading a new version.']);
      return;
    }

    if (files.length === 0) {
      setValidationErrors(['Please upload at least one PDF document']);
      return;
    }

    setUploading(true);
    setError('');
    setSuccess(false);
    setValidationErrors([]);

    // Initialize progress for all files
    const initialProgress = new Map<string, FileProgress>();
    files.forEach((file) => {
      initialProgress.set(file.name, {
        fileName: file.name,
        progress: 0,
        status: 'pending',
        size: file.size,
      });
    });
    setFileProgress(initialProgress);

    try {
      let targetApplicationId = existingApplicationId ?? createdApplicationId;
      if (!isVersionUpload) {
        const created = await api.createApplication({
          application_ref: applicationRef.trim(),
          applicant_name: applicantName.trim() || undefined,
        });
        targetApplicationId = created.id ?? null;
        setCreatedApplicationId(targetApplicationId);
      }

      // Upload files one by one with individual progress tracking
      let lastRunId: number | null = null;
      let failedFiles: string[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // Update status to uploading
        setFileProgress((prev) => {
          const updated = new Map(prev);
          updated.set(file.name, {
            ...updated.get(file.name)!,
            status: 'uploading',
          });
          return updated;
        });

        try {
          const uploadHandler = isVersionUpload && existingApplicationId
            ? api.uploadApplicationRun.bind(null, existingApplicationId)
            : api.uploadFiles.bind(null, applicationRef.trim());

          const result = await uploadHandler([file], (progress: number) => {
            setFileProgress((prev) => {
              const updated = new Map(prev);
              updated.set(file.name, {
                ...updated.get(file.name)!,
                progress,
              });
              return updated;
            });
          });

          // Update to completed
          setFileProgress((prev) => {
            const updated = new Map(prev);
            updated.set(file.name, {
              ...updated.get(file.name)!,
              progress: 100,
              status: 'completed',
            });
            return updated;
          });

          if (result.run_id) {
            lastRunId = result.run_id;
            setLastRunId(result.run_id);
          }
        } catch (fileErr: any) {
          console.error(`Upload error for ${file.name}:`, fileErr);
          const errorMessage = fileErr.response?.data?.detail || fileErr.message || 'Upload failed';

          failedFiles.push(file.name);

          setFileProgress((prev) => {
            const updated = new Map(prev);
            updated.set(file.name, {
              ...updated.get(file.name)!,
              progress: 0,
              status: 'error',
              error: errorMessage,
            });
            return updated;
          });
        }
      }

      if (failedFiles.length === 0) {
        setSuccess(true);

        // Navigate to results after 3 seconds (give user time to see success)
        setTimeout(() => {
          if (lastRunId && targetApplicationId) {
            navigate(`/applications/${targetApplicationId}/runs/${lastRunId}`);
          } else {
            navigate('/my-cases');
          }
        }, 3000);
      } else {
        setError(`${failedFiles.length} file(s) failed to upload. You can retry individual files below.`);
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      const message = getApiErrorMessage(err, 'Upload failed. Please try again.');
      if (message.includes('network issue') || message.includes('CORS')) {
        setBackendAvailable(false);
      }
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / 1024 / 1024;
    if (mb < 10) return `${mb.toFixed(2)} MB`;
    return `${mb.toFixed(1)} MB`;
  };

  const getFileProgressColor = (size: number): 'default' | 'warning' | 'error' => {
    const mb = size / 1024 / 1024;
    if (mb > 150) return 'error';
    if (mb > 100) return 'warning';
    return 'default';
  };

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom fontWeight="bold">
        {isVersionUpload ? 'Upload New Version' : 'New Planning Application'}
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={3}>
        {isVersionUpload
          ? 'Create a new processing run for an existing case.'
          : 'Upload planning documents for automated validation'}
      </Typography>

      {isVersionUpload && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You are uploading a new version for case <strong>{applicationRef || 'Loading...'}</strong>.
          This will create a new run without creating a new application record.
        </Alert>
      )}

      {/* Backend Status Alert */}
      {backendAvailable === false && (
        <Alert severity="error" sx={{ mb: 2 }} action={
          <Button color="inherit" size="small" onClick={checkBackendHealth} startIcon={<Refresh />}>
            Retry
          </Button>
        }>
          <AlertTitle>Backend Offline</AlertTitle>
          Cannot connect to backend server. Please ensure the backend is running on port 8000.
        </Alert>
      )}

      {backendAvailable && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Backend server is connected and healthy
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Application Reference */}
            <TextField
              label="Application Reference *"
              value={applicationRef}
              onChange={(e) => {
                setApplicationRef(e.target.value);
                setValidationErrors([]);
              }}
              placeholder="e.g., APP-2025-001, APP/2025/001"
              required
              fullWidth
              disabled={uploading || isVersionUpload || loadingApplication}
              error={validationErrors.some(e => e.toLowerCase().includes('reference'))}
              helperText={isVersionUpload
                ? 'Locked to the selected case.'
                : 'Required. Alphanumeric, hyphens, and slashes allowed.'}
            />

            {/* Applicant Name */}
            <TextField
              label="Applicant Name (Optional)"
              value={applicantName}
              onChange={(e) => setApplicantName(e.target.value)}
              placeholder="Enter applicant name"
              fullWidth
              disabled={uploading || isVersionUpload || loadingApplication}
            />

            {/* File Upload */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Upload Documents
              </Typography>
              <Box
                {...getRootProps()}
                sx={{
                  border: '2px dashed',
                  borderColor: isDragActive ? 'primary.main' : 'divider',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  bgcolor: isDragActive ? 'action.hover' : 'background.default',
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': { bgcolor: uploading ? 'background.default' : 'action.hover' },
                  opacity: uploading ? 0.6 : 1,
                }}
              >
                <input {...getInputProps()} disabled={uploading} />
                <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="body1" gutterBottom>
                  {isDragActive ? 'Drop PDF files here' : 'Drag & drop PDF files here'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  or click to browse (Max 200MB per file)
                </Typography>
              </Box>
            </Box>

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <Alert severity="warning" onClose={() => setValidationErrors([])}>
                <AlertTitle>Validation Issues</AlertTitle>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {validationErrors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </Alert>
            )}

            {/* File List */}
            {files.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Selected Files ({files.length})
                </Typography>
                {files.map((file, index) => {
                  const progress = fileProgress.get(file.name);
                  return (
                    <Box
                      key={index}
                      sx={{
                        p: 1.5,
                        mb: 1,
                        bgcolor: 'background.default',
                        borderRadius: 1,
                        border: '1px solid',
                        borderColor: progress?.status === 'error' ? 'error.main' : 'divider',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: progress ? 1 : 0 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, minWidth: 0 }}>
                          {progress?.status === 'completed' && <CheckCircle color="success" fontSize="small" />}
                          {progress?.status === 'error' && <ErrorIcon color="error" fontSize="small" />}
                          {progress?.status === 'uploading' && <CircularProgress size={16} />}

                          <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                            {file.name}
                          </Typography>

                          <Tooltip title={`${formatFileSize(file.size)}`}>
                            <Chip
                              label={formatFileSize(file.size)}
                              size="small"
                              color={getFileProgressColor(file.size)}
                            />
                          </Tooltip>
                        </Box>

                        <Box sx={{ display: 'flex', gap: 1 }}>
                          {progress?.status === 'error' && (
                            <Tooltip title="Retry upload">
                              <IconButton size="small" onClick={() => retryFile(file.name)} disabled={uploading}>
                                <Refresh />
                              </IconButton>
                            </Tooltip>
                          )}
                          {!uploading && !progress && (
                            <IconButton size="small" onClick={() => removeFile(index)}>
                              <Close />
                            </IconButton>
                          )}
                        </Box>
                      </Box>

                      {progress && progress.status !== 'pending' && (
                        <Box>
                          <LinearProgress
                            variant="determinate"
                            value={progress.progress}
                            color={progress.status === 'error' ? 'error' : progress.status === 'completed' ? 'success' : 'primary'}
                            sx={{ mb: 0.5 }}
                          />
                          {progress.error && (
                            <Typography variant="caption" color="error">
                              {progress.error}
                            </Typography>
                          )}
                          {progress.status === 'uploading' && (
                            <Typography variant="caption" color="text.secondary">
                              {progress.progress}% uploaded
                            </Typography>
                          )}
                          {progress.status === 'completed' && (
                            <Typography variant="caption" color="success.main">
                              Upload complete
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                  );
                })}
              </Box>
            )}

            {/* Error Message */}
            {error && (
              <Alert severity="error" onClose={() => setError('')}>
                <AlertTitle>Upload Error</AlertTitle>
                {error}
              </Alert>
            )}

            {/* Success Message */}
            {success && (
              <Alert severity="success">
                <AlertTitle>Success</AlertTitle>
                {isVersionUpload
                  ? 'New version uploaded successfully!'
                  : 'All files uploaded successfully!'}
                Redirecting to results...
              </Alert>
            )}

            {/* Submit Button */}
            <Button
              variant="contained"
              size="large"
              startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUpload />}
              onClick={handleSubmit}
              disabled={uploading || loadingApplication || files.length === 0 || !applicationRef.trim() || backendAvailable === false}
              fullWidth
            >
              {uploading ? 'Uploading...' : isVersionUpload ? 'Upload New Version' : 'Start Validation'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
