import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Stack,
  Divider,
  Grid,
} from '@mui/material';
import {
  CloudUpload,
  Visibility,
  Refresh,
  CheckCircle,
  Error,
  HourglassEmpty,
  RateReview,
} from '@mui/icons-material';
import api from '../api/client';

interface ValidationSummary {
  pass: number;
  fail: number;
  warning: number;
  needs_review: number;
}

interface RunHistoryItem {
  id: number;
  created_at: string;
  status: string;
  validation_summary: ValidationSummary;
}

interface ApplicationDetailsData {
  id: number;
  reference_number: string;
  address: string;
  proposal: string;
  applicant_name: string;
  created_at: string;
  status: string;
  run_history: RunHistoryItem[];
}

const ApplicationDetails: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [appData, setAppData] = useState<ApplicationDetailsData | null>(null);

  useEffect(() => {
    loadApplicationDetails();
  }, [applicationId]);

  const loadApplicationDetails = async () => {
    if (!applicationId) {
      setError('Application ID is required');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError('');
      const response = await api.getApplicationDetails(parseInt(applicationId));
      setAppData(response);
    } catch (err: any) {
      console.error('Failed to load application details:', err);
      setError(err.message || 'Failed to load application details');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const statusMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
      pending: 'default',
      processing: 'info',
      completed: 'success',
      reviewed: 'success',
      failed: 'error',
    };
    return statusMap[status] || 'default';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'reviewed':
        return <CheckCircle fontSize="small" />;
      case 'processing':
        return <HourglassEmpty fontSize="small" />;
      case 'failed':
        return <Error fontSize="small" />;
      default:
        return null;
    }
  };

  const handleUploadNewVersion = () => {
    // Navigate to upload page with pre-filled application data
    navigate('/new-application', {
      state: {
        applicationId: appData?.id,
        applicationRef: appData?.reference_number,
        applicantName: appData?.applicant_name,
      },
    });
  };

  const handleViewResults = (runId: number) => {
    navigate(`/applications/${applicationId}/runs/${runId}`);
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" onClose={() => setError('')}>
          {error}
        </Alert>
        <Box sx={{ mt: 2 }}>
          <Button variant="outlined" onClick={() => navigate('/my-cases')}>
            Back to My Cases
          </Button>
        </Box>
      </Container>
    );
  }

  if (!appData) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="warning">Application not found</Alert>
        <Box sx={{ mt: 2 }}>
          <Button variant="outlined" onClick={() => navigate('/my-cases')}>
            Back to My Cases
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {appData.reference_number}
            </Typography>
            <Chip
              label={appData.status}
              color={getStatusColor(appData.status)}
              icon={getStatusIcon(appData.status)}
              sx={{ mr: 1 }}
            />
          </Box>
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={loadApplicationDetails}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<CloudUpload />}
              onClick={handleUploadNewVersion}
            >
              Upload New Version
            </Button>
          </Stack>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Case Metadata */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Address
            </Typography>
            <Typography variant="body1" gutterBottom>
              {appData.address}
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Applicant
            </Typography>
            <Typography variant="body1" gutterBottom>
              {appData.applicant_name}
            </Typography>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="subtitle2" color="text.secondary">
              Proposal
            </Typography>
            <Typography variant="body1" gutterBottom>
              {appData.proposal}
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Submitted
            </Typography>
            <Typography variant="body1">
              {new Date(appData.created_at).toLocaleDateString('en-GB', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Run History */}
      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Run History
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {appData.run_history.length} processing run(s)
        </Typography>

        {appData.run_history.length === 0 ? (
          <Alert severity="info">
            No processing runs yet. Upload documents to start validation.
          </Alert>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Run ID</TableCell>
                  <TableCell>Date & Time</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="center">Pass</TableCell>
                  <TableCell align="center">Fail</TableCell>
                  <TableCell align="center">Warning</TableCell>
                  <TableCell align="center">Needs Review</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {appData.run_history.map((run) => (
                  <TableRow key={run.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        #{run.id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {new Date(run.created_at).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={run.status}
                        color={getStatusColor(run.status)}
                        size="small"
                        icon={getStatusIcon(run.status)}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={run.validation_summary.pass}
                        size="small"
                        color="success"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={run.validation_summary.fail}
                        size="small"
                        color="error"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={run.validation_summary.warning}
                        size="small"
                        color="warning"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={run.validation_summary.needs_review}
                        size="small"
                        color="info"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<Visibility />}
                          onClick={() => handleViewResults(run.id)}
                          disabled={run.status === 'processing' || run.status === 'pending'}
                        >
                          View Results
                        </Button>
                        {run.status === 'completed' && run.validation_summary.needs_review > 0 && (
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<RateReview />}
                            onClick={() => navigate(`/applications/${applicationId}/runs/${run.id}/review`)}
                          >
                            Start Review
                          </Button>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Container>
  );
};

export default ApplicationDetails;
