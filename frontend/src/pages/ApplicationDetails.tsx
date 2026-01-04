import React, { useState, useEffect, useRef } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  Skeleton,
  TablePagination,
} from '@mui/material';
import {
  CloudUpload,
  Visibility,
  Refresh,
  CheckCircle,
  Error,
  HourglassEmpty,
  RateReview,
  CompareArrows,
  Description,
} from '@mui/icons-material';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errorUtils';
import BNGDecision from '../components/BNGDecision';

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
  application_type: string;
  created_at: string;
  status: string;
  run_history: RunHistoryItem[];
}

interface ComparisonFinding {
  rule_id: string;
  title: string;
  status: string;
  severity: string;
  message: string;
  document_id?: number;
  document_name?: string | null;
  from_status?: string;
  to_status?: string;
}

interface ComparisonFieldChange {
  field: string;
  value?: string;
  old_value?: string;
  new_value?: string;
  document_id?: number;
  document_name?: string | null;
}

interface ComparisonDocument {
  id: number;
  filename: string;
  content_hash?: string | null;
  document_type?: string | null;
}

interface ComparisonDocumentChange {
  filename: string;
  old_content_hashes: string[];
  new_content_hashes: string[];
  old_document_types: string[];
  new_document_types: string[];
  old_document_ids: number[];
  new_document_ids: number[];
}

interface RunComparison {
  run_a: { id: number; created_at: string | null };
  run_b: { id: number; created_at: string | null };
  findings: {
    new_issues: ComparisonFinding[];
    resolved_issues: ComparisonFinding[];
    status_changes: ComparisonFinding[];
  };
  documents: {
    added_documents: ComparisonDocument[];
    removed_documents: ComparisonDocument[];
    changed_documents: ComparisonDocumentChange[];
  };
  extracted_fields: {
    added: ComparisonFieldChange[];
    removed: ComparisonFieldChange[];
    changed: ComparisonFieldChange[];
  };
}

const ApplicationDetails: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [appData, setAppData] = useState<ApplicationDetailsData | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareRunIdA, setCompareRunIdA] = useState<number | ''>('');
  const [compareRunIdB, setCompareRunIdB] = useState<number | ''>('');
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');
  const [comparison, setComparison] = useState<RunComparison | null>(null);
  const [runPage, setRunPage] = useState(0);
  const [runsPerPage, setRunsPerPage] = useState(5);
  const [downloadingReportRunId, setDownloadingReportRunId] = useState<number | null>(null);
  const prefetchedRunsRef = useRef(new Set<number>());
  const [latestRunResults, setLatestRunResults] = useState<any>(null);
  const [latestRunLoading, setLatestRunLoading] = useState(false);
  const [latestRunError, setLatestRunError] = useState('');

  useEffect(() => {
    loadApplicationDetails();
  }, [applicationId]);

  useEffect(() => {
    if (appData?.run_history) {
      // Only select runs that have documents for comparison
      const comparableRuns = appData.run_history.filter((r: any) => r.has_documents);
      if (comparableRuns.length >= 2) {
        setCompareRunIdB(comparableRuns[0].id);
        setCompareRunIdA(comparableRuns[1].id);
      } else if (comparableRuns.length === 1) {
        setCompareRunIdB(comparableRuns[0].id);
        setCompareRunIdA('');
      }
    }
  }, [appData]);

  useEffect(() => {
    setRunPage(0);
  }, [appData?.run_history.length]);

  const latestRunId = appData?.run_history?.[0]?.id;

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
      setError(getApiErrorMessage(err, 'Failed to load application details'));
    } finally {
      setLoading(false);
    }
  };

  const loadLatestRunResults = async (runId: number) => {
    try {
      setLatestRunLoading(true);
      setLatestRunError('');
      const results = await api.getRunResults(runId);
      setLatestRunResults(results);
    } catch (err: any) {
      console.error('Failed to load latest run results:', err);
      setLatestRunError(getApiErrorMessage(err, 'Failed to load BNG decision data'));
    } finally {
      setLatestRunLoading(false);
    }
  };

  useEffect(() => {
    if (!latestRunId) {
      setLatestRunResults(null);
      return;
    }

    loadLatestRunResults(latestRunId);
  }, [latestRunId]);

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
        return undefined;
    }
  };

  const formatDocumentMeta = (doc: ComparisonDocument) => {
    const details: string[] = [];
    if (doc.document_type) {
      details.push(`Type: ${doc.document_type}`);
    }
    if (doc.content_hash) {
      details.push(`Hash: ${doc.content_hash}`);
    }
    return details.length > 0 ? details.join(' • ') : 'No metadata';
  };

  const formatDocumentChangeDetail = (
    label: string,
    oldValues: string[],
    newValues: string[]
  ) => {
    const oldLabel = oldValues.length > 0 ? oldValues.join(', ') : 'None';
    const newLabel = newValues.length > 0 ? newValues.join(', ') : 'None';
    return `${label}: ${oldLabel} → ${newLabel}`;
  };

  const handleUploadNewVersion = () => {
    // Navigate to upload page with pre-filled application data
    navigate('/new-application', {
      state: {
        applicationId: appData?.id,
        applicationRef: appData?.reference_number,
        applicantName: appData?.applicant_name,
        applicationType: appData?.application_type,
      },
    });
  };

  const handleViewResults = (runId: number) => {
    navigate(`/applications/${applicationId}/runs/${runId}`);
  };

  const prefetchRunResults = async (runId: number) => {
    if (prefetchedRunsRef.current.has(runId)) {
      return;
    }
    prefetchedRunsRef.current.add(runId);
    try {
      const results = await api.getRunResults(runId);
      sessionStorage.setItem(`run-results-${runId}`, JSON.stringify(results));
    } catch (err) {
      prefetchedRunsRef.current.delete(runId);
      console.warn('Failed to prefetch run results:', err);
    }
  };

  const handleDownloadReport = async (runId: number) => {
    try {
      setDownloadingReportRunId(runId);
      const blob = await api.downloadReviewReport(runId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `run-${runId}-hil-review-report.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Failed to download report'));
    } finally {
      setDownloadingReportRunId(null);
    }
  };

  const handleOpenCompare = () => {
    setCompareError('');
    setComparison(null);
    setCompareOpen(true);
  };

  const handleCompareRuns = async () => {
    if (!compareRunIdA || !compareRunIdB) {
      setCompareError('Select two runs to compare.');
      return;
    }
    if (compareRunIdA === compareRunIdB) {
      setCompareError('Please select two different runs.');
      return;
    }

    try {
      setCompareLoading(true);
      setCompareError('');
      const response = await api.compareRuns(compareRunIdA, compareRunIdB);
      setComparison(response);
    } catch (err: any) {
      console.error('Failed to compare runs:', err);
      setCompareError(getApiErrorMessage(err, 'Failed to compare runs'));
    } finally {
      setCompareLoading(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="40%" height={40} />
              <Skeleton variant="rounded" width={120} height={32} />
            </Box>
            <Stack direction="row" spacing={2}>
              <Skeleton variant="rounded" width={120} height={36} />
              <Skeleton variant="rounded" width={180} height={36} />
            </Stack>
          </Box>
          <Divider sx={{ my: 2 }} />
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Skeleton variant="text" width="30%" />
              <Skeleton variant="text" width="80%" />
            </Grid>
            <Grid item xs={12} md={6}>
              <Skeleton variant="text" width="30%" />
              <Skeleton variant="text" width="80%" />
            </Grid>
            <Grid item xs={12}>
              <Skeleton variant="text" width="20%" />
              <Skeleton variant="text" width="90%" />
            </Grid>
          </Grid>
        </Paper>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Skeleton variant="text" width="30%" height={32} sx={{ mb: 2 }} />
          <Stack spacing={2}>
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} variant="rounded" height={56} />
            ))}
          </Stack>
        </Paper>
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

  const pagedRuns = appData.run_history.slice(
    runPage * runsPerPage,
    runPage * runsPerPage + runsPerPage
  );

  const resolveBNGStatus = () => {
    const submissionFields = latestRunResults?.submission_fields || {};
    const extractedFields = latestRunResults?.extracted_fields || {};
    const rawApplicable =
      submissionFields.bng_applicable ??
      extractedFields.bng_applicable ??
      latestRunResults?.bng_applicable;
    let applicable: boolean | null = null;
    if (typeof rawApplicable === 'boolean') {
      applicable = rawApplicable;
    } else if (typeof rawApplicable === 'string') {
      const normalized = rawApplicable.toLowerCase();
      if (['true', 'yes', '1'].includes(normalized)) {
        applicable = true;
      } else if (['false', 'no', '0'].includes(normalized)) {
        applicable = false;
      }
    }

    const exemptionReason =
      submissionFields.bng_exemption_reason ??
      extractedFields.bng_exemption_reason ??
      latestRunResults?.bng_exemption_reason ??
      '';

    return { applicable, exemptionReason };
  };

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
            {appData.run_history.length >= 2 && (
              <Button
                variant="outlined"
                startIcon={<CompareArrows />}
                onClick={handleOpenCompare}
              >
                Compare Runs
              </Button>
            )}
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
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Application Type
            </Typography>
            <Typography variant="body1" gutterBottom>
              {appData.application_type ? appData.application_type.replace(/_/g, ' ') : 'Unknown'}
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

      {latestRunId && (
        <Box sx={{ mb: 3 }}>
          {latestRunError && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {latestRunError}
            </Alert>
          )}
          {latestRunLoading ? (
            <Paper elevation={2} sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress size={24} />
            </Paper>
          ) : (
            <BNGDecision
              runId={latestRunId}
              currentBNGStatus={resolveBNGStatus()}
              onDecisionSubmitted={() => loadLatestRunResults(latestRunId)}
            />
          )}
        </Box>
      )}

      <Dialog open={compareOpen} onClose={() => setCompareOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Compare Runs</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            {/* Info about comparable runs */}
            {appData.run_history.filter((r: any) => r.has_documents).length < 2 && (
              <Alert severity="warning">
                At least 2 runs with documents are needed to compare. 
                Only runs with documents can be compared.
              </Alert>
            )}
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <FormControl fullWidth>
                <InputLabel id="compare-run-a-label">Base Run</InputLabel>
                <Select
                  labelId="compare-run-a-label"
                  value={compareRunIdA}
                  label="Base Run"
                  onChange={(event) => setCompareRunIdA(event.target.value as number)}
                >
                  {appData.run_history
                    .filter((run: any) => run.has_documents)
                    .map((run: any) => (
                    <MenuItem key={run.id} value={run.id}>
                      Run #{run.id} • {new Date(run.created_at).toLocaleDateString('en-GB')}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel id="compare-run-b-label">Comparison Run</InputLabel>
                <Select
                  labelId="compare-run-b-label"
                  value={compareRunIdB}
                  label="Comparison Run"
                  onChange={(event) => setCompareRunIdB(event.target.value as number)}
                >
                  {appData.run_history
                    .filter((run: any) => run.has_documents)
                    .map((run: any) => (
                    <MenuItem key={run.id} value={run.id}>
                      Run #{run.id} • {new Date(run.created_at).toLocaleDateString('en-GB')}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>

            {compareError && <Alert severity="error">{compareError}</Alert>}

            {compareLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress size={24} />
              </Box>
            )}

            {comparison && !compareLoading && (
              <Stack spacing={3}>
                {/* Summary Cards */}
                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.50', border: '1px solid', borderColor: 'error.200' }}>
                    <Typography variant="h4" color="error.main" fontWeight="bold">
                      {comparison.findings.new_issues.length}
                    </Typography>
                    <Typography variant="body2" color="error.dark">New Issues</Typography>
                  </Paper>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.50', border: '1px solid', borderColor: 'success.200' }}>
                    <Typography variant="h4" color="success.main" fontWeight="bold">
                      {comparison.findings.resolved_issues.length}
                    </Typography>
                    <Typography variant="body2" color="success.dark">Resolved</Typography>
                  </Paper>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'info.50', border: '1px solid', borderColor: 'info.200' }}>
                    <Typography variant="h4" color="info.main" fontWeight="bold">
                      {comparison.documents.added_documents.length + comparison.documents.removed_documents.length}
                    </Typography>
                    <Typography variant="body2" color="info.dark">Doc Changes</Typography>
                  </Paper>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'warning.50', border: '1px solid', borderColor: 'warning.200' }}>
                    <Typography variant="h4" color="warning.main" fontWeight="bold">
                      {comparison.extracted_fields.added.length + comparison.extracted_fields.removed.length + comparison.extracted_fields.changed.length}
                    </Typography>
                    <Typography variant="body2" color="warning.dark">Field Changes</Typography>
                  </Paper>
                </Box>

                {/* Findings Section */}
                {(comparison.findings.new_issues.length > 0 || comparison.findings.resolved_issues.length > 0 || comparison.findings.status_changes.length > 0) && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                      🔍 Validation Findings
                    </Typography>
                    
                    {comparison.findings.new_issues.length > 0 && (
                      <Box sx={{ mb: 2 }}>
                        <Chip label="New Issues" color="error" size="small" sx={{ mb: 1 }} />
                        <Stack spacing={1}>
                          {comparison.findings.new_issues.map((item, idx) => (
                            <Paper key={idx} variant="outlined" sx={{ p: 1.5, bgcolor: 'error.50', borderColor: 'error.200' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip label={item.rule_id || item.title} size="small" />
                                <Chip label={item.status} size="small" color="error" variant="outlined" />
                              </Box>
                              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                                {item.document_name || 'Unknown document'}
                              </Typography>
                            </Paper>
                          ))}
                        </Stack>
                      </Box>
                    )}
                    
                    {comparison.findings.resolved_issues.length > 0 && (
                      <Box sx={{ mb: 2 }}>
                        <Chip label="Resolved" color="success" size="small" sx={{ mb: 1 }} />
                        <Stack spacing={1}>
                          {comparison.findings.resolved_issues.map((item, idx) => (
                            <Paper key={idx} variant="outlined" sx={{ p: 1.5, bgcolor: 'success.50', borderColor: 'success.200' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip label={item.rule_id || item.title} size="small" />
                                <Typography variant="body2" color="success.dark">✓ Fixed</Typography>
                              </Box>
                              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                                {item.document_name || 'Unknown document'}
                              </Typography>
                            </Paper>
                          ))}
                        </Stack>
                      </Box>
                    )}

                    {comparison.findings.status_changes.length > 0 && (
                      <Box>
                        <Chip label="Status Changes" color="warning" size="small" sx={{ mb: 1 }} />
                        <Stack spacing={1}>
                          {comparison.findings.status_changes.map((item, idx) => (
                            <Paper key={idx} variant="outlined" sx={{ p: 1.5, bgcolor: 'warning.50', borderColor: 'warning.200' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip label={item.rule_id || item.title} size="small" />
                                <Chip label={item.from_status} size="small" variant="outlined" />
                                <Typography variant="body2">→</Typography>
                                <Chip label={item.to_status} size="small" color="primary" />
                              </Box>
                            </Paper>
                          ))}
                        </Stack>
                      </Box>
                    )}
                  </Paper>
                )}

                {/* Documents Section */}
                {(comparison.documents.added_documents.length > 0 || comparison.documents.removed_documents.length > 0) && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                      📄 Document Changes
                    </Typography>
                    
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
                      {comparison.documents.added_documents.length > 0 && (
                        <Box>
                          <Chip label={`${comparison.documents.added_documents.length} Added`} color="success" size="small" sx={{ mb: 1 }} />
                          <Stack spacing={1}>
                            {comparison.documents.added_documents.map((doc, idx) => (
                              <Paper key={idx} variant="outlined" sx={{ p: 1.5, bgcolor: 'success.50' }}>
                                <Typography variant="body2" fontWeight="medium" noWrap>
                                  {doc.filename?.slice(0, 40)}{doc.filename?.length > 40 ? '...' : ''}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {doc.document_type || 'Unknown type'}
                                </Typography>
                              </Paper>
                            ))}
                          </Stack>
                        </Box>
                      )}
                      
                      {comparison.documents.removed_documents.length > 0 && (
                        <Box>
                          <Chip label={`${comparison.documents.removed_documents.length} Removed`} color="error" size="small" sx={{ mb: 1 }} />
                          <Stack spacing={1}>
                            {comparison.documents.removed_documents.map((doc, idx) => (
                              <Paper key={idx} variant="outlined" sx={{ p: 1.5, bgcolor: 'error.50' }}>
                                <Typography variant="body2" fontWeight="medium" noWrap sx={{ textDecoration: 'line-through' }}>
                                  {doc.filename?.slice(0, 40)}{doc.filename?.length > 40 ? '...' : ''}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {doc.document_type || 'Unknown type'}
                                </Typography>
                              </Paper>
                            ))}
                          </Stack>
                        </Box>
                      )}
                    </Box>
                  </Paper>
                )}

                {/* Extracted Fields Section */}
                {(comparison.extracted_fields.added.length > 0 || comparison.extracted_fields.removed.length > 0 || comparison.extracted_fields.changed.length > 0) && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                      📝 Extracted Data Changes
                    </Typography>
                    
                    {comparison.extracted_fields.changed.length > 0 && (
                      <Box sx={{ mb: 2 }}>
                        <Chip label={`${comparison.extracted_fields.changed.length} Updated`} color="primary" size="small" sx={{ mb: 1 }} />
                        <TableContainer component={Paper} variant="outlined">
                          <Table size="small">
                            <TableHead>
                              <TableRow sx={{ bgcolor: 'grey.100' }}>
                                <TableCell><strong>Field</strong></TableCell>
                                <TableCell><strong>Old Value</strong></TableCell>
                                <TableCell><strong>New Value</strong></TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {comparison.extracted_fields.changed.slice(0, 10).map((item, idx) => (
                                <TableRow key={idx}>
                                  <TableCell>
                                    <Typography variant="body2" fontWeight="medium">{item.field}</Typography>
                                  </TableCell>
                                  <TableCell>
                                    <Typography variant="body2" color="error.main" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                      {String(item.old_value).slice(0, 50)}{String(item.old_value).length > 50 ? '...' : ''}
                                    </Typography>
                                  </TableCell>
                                  <TableCell>
                                    <Typography variant="body2" color="success.main" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                      {String(item.new_value).slice(0, 50)}{String(item.new_value).length > 50 ? '...' : ''}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                        {comparison.extracted_fields.changed.length > 10 && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                            +{comparison.extracted_fields.changed.length - 10} more changes...
                          </Typography>
                        )}
                      </Box>
                    )}

                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
                      {comparison.extracted_fields.added.length > 0 && (
                        <Box>
                          <Chip label={`${comparison.extracted_fields.added.length} New Fields`} color="success" size="small" sx={{ mb: 1 }} />
                          <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'success.50', maxHeight: 200, overflow: 'auto' }}>
                            {comparison.extracted_fields.added.slice(0, 8).map((item, idx) => (
                              <Box key={idx} sx={{ mb: 1, pb: 1, borderBottom: idx < 7 ? '1px solid' : 'none', borderColor: 'divider' }}>
                                <Typography variant="body2" fontWeight="medium">{item.field}</Typography>
                                <Typography variant="caption" color="text.secondary" noWrap>
                                  {String(item.value).slice(0, 60)}{String(item.value).length > 60 ? '...' : ''}
                                </Typography>
                              </Box>
                            ))}
                            {comparison.extracted_fields.added.length > 8 && (
                              <Typography variant="caption" color="text.secondary">
                                +{comparison.extracted_fields.added.length - 8} more...
                              </Typography>
                            )}
                          </Paper>
                        </Box>
                      )}
                      
                      {comparison.extracted_fields.removed.length > 0 && (
                        <Box>
                          <Chip label={`${comparison.extracted_fields.removed.length} Removed Fields`} color="error" size="small" sx={{ mb: 1 }} />
                          <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'error.50', maxHeight: 200, overflow: 'auto' }}>
                            {comparison.extracted_fields.removed.slice(0, 8).map((item, idx) => (
                              <Box key={idx} sx={{ mb: 1, pb: 1, borderBottom: idx < 7 ? '1px solid' : 'none', borderColor: 'divider' }}>
                                <Typography variant="body2" fontWeight="medium" sx={{ textDecoration: 'line-through' }}>{item.field}</Typography>
                                <Typography variant="caption" color="text.secondary" noWrap>
                                  {String(item.value).slice(0, 60)}{String(item.value).length > 60 ? '...' : ''}
                                </Typography>
                              </Box>
                            ))}
                            {comparison.extracted_fields.removed.length > 8 && (
                              <Typography variant="caption" color="text.secondary">
                                +{comparison.extracted_fields.removed.length - 8} more...
                              </Typography>
                            )}
                          </Paper>
                        </Box>
                      )}
                    </Box>
                  </Paper>
                )}

                {/* No Changes Message */}
                {comparison.findings.new_issues.length === 0 && 
                 comparison.findings.resolved_issues.length === 0 && 
                 comparison.documents.added_documents.length === 0 && 
                 comparison.documents.removed_documents.length === 0 &&
                 comparison.extracted_fields.added.length === 0 && 
                 comparison.extracted_fields.removed.length === 0 &&
                 comparison.extracted_fields.changed.length === 0 && (
                  <Alert severity="info" icon={<span>✨</span>}>
                    No significant changes detected between these runs.
                  </Alert>
                )}
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompareOpen(false)} variant="text">
            Close
          </Button>
          <Button
            onClick={handleCompareRuns}
            variant="contained"
            disabled={compareLoading}
          >
            Compare
          </Button>
        </DialogActions>
      </Dialog>

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
                {pagedRuns.map((run) => (
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
                          onMouseEnter={() => {
                            if (run.status !== 'processing' && run.status !== 'pending') {
                              prefetchRunResults(run.id);
                            }
                          }}
                          onFocus={() => {
                            if (run.status !== 'processing' && run.status !== 'pending') {
                              prefetchRunResults(run.id);
                            }
                          }}
                          disabled={run.status === 'processing' || run.status === 'pending'}
                        >
                          View Results
                        </Button>
                        {run.status === 'reviewed' && (
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<Description />}
                            onClick={() => handleDownloadReport(run.id)}
                            disabled={downloadingReportRunId === run.id}
                          >
                            {downloadingReportRunId === run.id ? 'Preparing...' : 'Download report'}
                          </Button>
                        )}
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
            <TablePagination
              component="div"
              count={appData.run_history.length}
              page={runPage}
              onPageChange={(_, newPage) => setRunPage(newPage)}
              rowsPerPage={runsPerPage}
              onRowsPerPageChange={(event) => {
                setRunsPerPage(parseInt(event.target.value, 10));
                setRunPage(0);
              }}
              rowsPerPageOptions={[5, 10, 20]}
            />
          </TableContainer>
        )}
      </Paper>
    </Container>
  );
};

export default ApplicationDetails;
