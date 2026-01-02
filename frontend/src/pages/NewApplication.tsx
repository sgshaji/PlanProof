import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import { CloudUpload, Close, CheckCircle } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { api } from '../api/client';
import type { UploadProgress } from '../types';

export default function NewApplication() {
  const navigate = useNavigate();
  const [applicationRef, setApplicationRef] = useState('');
  const [applicantName, setApplicantName] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    onDrop: (acceptedFiles) => {
      setFiles((prev) => [...prev, ...acceptedFiles]);
      setError('');
    },
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!applicationRef.trim()) {
      setError('Application reference is required');
      return;
    }
    if (files.length === 0) {
      setError('Please upload at least one PDF document');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess(false);

    try {
      // Try to create application (ignore if already exists)
      try {
        await api.createApplication({
          application_ref: applicationRef,
          applicant_name: applicantName || undefined,
        });
      } catch (createErr: any) {
        // Ignore 409 Conflict (application exists) - just continue to upload
        if (createErr.response?.status !== 409) {
          throw createErr;
        }
        console.log('Application already exists, continuing with upload...');
      }

      // Upload files with progress tracking
      const result = await api.uploadFiles(
        applicationRef,
        files,
        (progress) => {
          setUploadProgress(
            files.map((file) => ({
              fileName: file.name,
              progress,
              status: 'uploading',
            }))
          );
        }
      );

      setSuccess(true);
      setUploadProgress(
        files.map((file) => ({
          fileName: file.name,
          progress: 100,
          status: 'completed',
        }))
      );

      // Navigate to results after 2 seconds
      setTimeout(() => {
        if (result.run_id) {
          navigate(`/results/${result.run_id}`);
        } else {
          navigate('/my-cases');
        }
      }, 2000);
    } catch (err: any) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed. Please try again.';
      setError(errorMessage);
      setUploadProgress(
        files.map((file) => ({
          fileName: file.name,
          progress: 0,
          status: 'error',
          error: errorMessage,
        }))
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom fontWeight="bold">
        📤 New Planning Application
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={3}>
        Upload planning documents for automated validation
      </Typography>

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Application Reference */}
            <TextField
              label="Application Reference"
              value={applicationRef}
              onChange={(e) => setApplicationRef(e.target.value)}
              placeholder="e.g., APP-2025-001"
              required
              fullWidth
              disabled={uploading}
            />

            {/* Applicant Name */}
            <TextField
              label="Applicant Name (Optional)"
              value={applicantName}
              onChange={(e) => setApplicantName(e.target.value)}
              placeholder="Enter applicant name"
              fullWidth
              disabled={uploading}
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
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <input {...getInputProps()} />
                <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="body1" gutterBottom>
                  {isDragActive ? 'Drop files here' : 'Drag & drop PDF files here'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  or click to browse (Max 200MB per file)
                </Typography>
              </Box>
            </Box>

            {/* File List */}
            {files.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Selected Files ({files.length})
                </Typography>
                {files.map((file, index) => (
                  <Box
                    key={index}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      p: 1.5,
                      mb: 1,
                      bgcolor: 'background.default',
                      borderRadius: 1,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                      <Typography variant="body2" noWrap>
                        {file.name}
                      </Typography>
                      <Chip
                        label={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                        size="small"
                      />
                    </Box>
                    {!uploading && (
                      <IconButton size="small" onClick={() => removeFile(index)}>
                        <Close />
                      </IconButton>
                    )}
                  </Box>
                ))}
              </Box>
            )}

            {/* Upload Progress */}
            {uploadProgress.length > 0 && (
              <Box>
                {uploadProgress.map((item, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                        {item.fileName}
                      </Typography>
                      {item.status === 'completed' && <CheckCircle color="success" />}
                      {item.status === 'error' && (
                        <Chip label="Error" color="error" size="small" />
                      )}
                      {item.status === 'uploading' && (
                        <Typography variant="caption">{item.progress}%</Typography>
                      )}
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={item.progress}
                      color={item.status === 'error' ? 'error' : 'primary'}
                    />
                  </Box>
                ))}
              </Box>
            )}

            {/* Error Message */}
            {error && (
              <Alert severity="error" onClose={() => setError('')}>
                {error}
              </Alert>
            )}

            {/* Success Message */}
            {success && (
              <Alert severity="success">
                ✅ Files uploaded successfully! Redirecting to results...
              </Alert>
            )}

            {/* Submit Button */}
            <Button
              variant="contained"
              size="large"
              startIcon={<CloudUpload />}
              onClick={handleSubmit}
              disabled={uploading || files.length === 0 || !applicationRef.trim()}
              fullWidth
            >
              {uploading ? 'Uploading...' : 'Start Validation'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
