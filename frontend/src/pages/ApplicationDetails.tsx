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

  useEffect(() => {
    loadApplicationDetails();
  }, [applicationId]);

  useEffect(() => {
    if (appData?.run_history.length && appData.run_history.length >= 2) {
      setCompareRunIdB(appData.run_history[0].id);
      setCompareRunIdA(appData.run_history[1].id);
    }
  }, [appData]);

  useEffect(() => {
    setRunPage(0);
  }, [appData?.run_history.length]);

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

      <Dialog open={compareOpen} onClose={() => setCompareOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Compare Runs</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <FormControl fullWidth>
                <InputLabel id="compare-run-a-label">Base Run</InputLabel>
                <Select
                  labelId="compare-run-a-label"
                  value={compareRunIdA}
                  label="Base Run"
                  onChange={(event) => setCompareRunIdA(event.target.value as number)}
                >
                  {appData.run_history.map((run) => (
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
                  {appData.run_history.map((run) => (
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
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Findings Changes
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    New issues: {comparison.findings.new_issues.length} • Resolved issues: {comparison.findings.resolved_issues.length} • Status changes: {comparison.findings.status_changes.length}
                  </Typography>
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="subtitle2">New Issues</Typography>
                      {comparison.findings.new_issues.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No new issues.</Typography>
                      ) : (
                        <List dense>
                          {comparison.findings.new_issues.map((item) => (
                            <ListItem key={`new-${item.rule_id}-${item.document_id}`}>
                              <ListItemText
                                primary={`${item.title} • ${item.status.toUpperCase()}`}
                                secondary={item.document_name || 'Unknown document'}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2">Resolved Issues</Typography>
                      {comparison.findings.resolved_issues.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No resolved issues.</Typography>
                      ) : (
                        <List dense>
                          {comparison.findings.resolved_issues.map((item) => (
                            <ListItem key={`resolved-${item.rule_id}-${item.document_id}`}>
                              <ListItemText
                                primary={`${item.title} • ${item.status.toUpperCase()}`}
                                secondary={item.document_name || 'Unknown document'}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2">Status Changes</Typography>
                      {comparison.findings.status_changes.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No status changes.</Typography>
                      ) : (
                        <List dense>
                          {comparison.findings.status_changes.map((item) => (
                            <ListItem key={`change-${item.rule_id}-${item.document_id}`}>
                              <ListItemText
                                primary={`${item.title} • ${item.from_status} → ${item.to_status}`}
                                secondary={item.document_name || 'Unknown document'}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                  </Stack>
                </Box>

                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Document Changes
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Added: {comparison.documents.added_documents.length} • Removed: {comparison.documents.removed_documents.length} • Updated: {comparison.documents.changed_documents.length}
                  </Typography>
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="subtitle2">Added Documents</Typography>
                      {comparison.documents.added_documents.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No added documents.</Typography>
                      ) : (
                        <List dense>
                          {comparison.documents.added_documents.map((doc) => (
                            <ListItem key={`doc-added-${doc.id}`}>
                              <ListItemText
                                primary={doc.filename}
                                secondary={formatDocumentMeta(doc)}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2">Removed Documents</Typography>
                      {comparison.documents.removed_documents.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No removed documents.</Typography>
                      ) : (
                        <List dense>
                          {comparison.documents.removed_documents.map((doc) => (
                            <ListItem key={`doc-removed-${doc.id}`}>
                              <ListItemText
                                primary={doc.filename}
                                secondary={formatDocumentMeta(doc)}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2">Updated Documents</Typography>
                      {comparison.documents.changed_documents.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No updated documents.</Typography>
                      ) : (
                        <List dense>
                          {comparison.documents.changed_documents.map((doc) => (
                            <ListItem key={`doc-changed-${doc.filename}`}>
                              <ListItemText
                                primary={doc.filename}
                                secondary={
                                  [
                                    formatDocumentChangeDetail('Type', doc.old_document_types, doc.new_document_types),
                                    formatDocumentChangeDetail('Hash', doc.old_content_hashes, doc.new_content_hashes),
                                  ].join(' • ')
                                }
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                  </Stack>
                </Box>

                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Extracted Field Changes
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Added: {comparison.extracted_fields.added.length} • Removed: {comparison.extracted_fields.removed.length} • Updated: {comparison.extracted_fields.changed.length}
                  </Typography>
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="subtitle2">Added Fields</Typography>
                      {comparison.extracted_fields.added.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No added fields.</Typography>
                      ) : (
                        <List dense>
                          {comparison.extracted_fields.added.map((item) => (
                            <ListItem key={`added-${item.field}-${item.document_id}`}>
                              <ListItemText
                                primary={`${item.field}: ${item.value}`}
                                secondary={item.document_name || 'Unknown document'}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2">Removed Fields</Typography>
                      {comparison.extracted_fields.removed.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No removed fields.</Typography>
                      ) : (
                        <List dense>
                          {comparison.extracted_fields.removed.map((item) => (
                            <ListItem key={`removed-${item.field}-${item.document_id}`}>
                              <ListItemText
                                primary={`${item.field}: ${item.value}`}
                                secondary={item.document_name || 'Unknown document'}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2">Updated Fields</Typography>
                      {comparison.extracted_fields.changed.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">No updated fields.</Typography>
                      ) : (
                        <List dense>
                          {comparison.extracted_fields.changed.map((item) => (
                            <ListItem key={`changed-${item.field}-${item.document_id}`}>
                              <ListItemText
                                primary={`${item.field}: ${item.old_value} → ${item.new_value}`}
                                secondary={item.document_name || 'Unknown document'}
                              />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </Box>
                  </Stack>
                </Box>
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
