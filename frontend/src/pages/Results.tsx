import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Chip,
  Alert,
  Button,
  Stack,
  List,
  ListItem,
  ListItemText,
  Paper,
  Container,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  Skeleton,
  LinearProgress,
} from '@mui/material';
import {
  RateReview,
  ArrowBack,
  Description,
  Error,
  Warning,
  Info,
  CheckCircle,
  ExpandMore,
  FindInPage,
  ThumbUp,
  ThumbDown,
} from '@mui/icons-material';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errorUtils';
import DocumentViewer from '../components/DocumentViewer';
import LLMTransparency from '../components/LLMTransparency';
import PriorApprovalDocs from '../components/PriorApprovalDocs';

export default function Results() {
  const { applicationId, runId } = useParams<{ applicationId: string; runId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [reclassifying, setReclassifying] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [viewerOpen, setViewerOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<any>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);

  const loadResults = async (isBackground = false) => {
    if (!runId) return;
    
    if (isBackground) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');
    try {
      const data = await api.getRunResults(parseInt(runId));
      setResults(data);
      sessionStorage.setItem(`run-results-${runId}`, JSON.stringify(data));
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Failed to load results'));
    } finally {
      if (isBackground) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (!runId) return;
    const cachedResults = sessionStorage.getItem(`run-results-${runId}`);
    if (cachedResults) {
      try {
        setResults(JSON.parse(cachedResults));
        setLoading(false);
      } catch (err) {
        console.warn('Failed to parse cached run results:', err);
      }
    }
    loadResults(Boolean(cachedResults));
  }, [runId]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="40%" height={40} />
              <Skeleton variant="text" width="30%" />
            </Box>
            <Stack direction="row" spacing={2}>
              <Skeleton variant="rounded" width={120} height={36} />
              <Skeleton variant="rounded" width={140} height={36} />
            </Stack>
          </Box>
          <Grid container spacing={2} sx={{ mt: 2 }}>
            {Array.from({ length: 4 }).map((_, index) => (
              <Grid item xs={6} md={3} key={index}>
                <Box sx={{ textAlign: 'center' }}>
                  <Skeleton variant="text" width="40%" height={32} sx={{ mx: 'auto' }} />
                  <Skeleton variant="text" width="60%" sx={{ mx: 'auto' }} />
                </Box>
              </Grid>
            ))}
          </Grid>
        </Paper>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Skeleton variant="text" width="25%" height={32} sx={{ mb: 2 }} />
          <Stack spacing={2}>
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} variant="rounded" height={56} />
            ))}
          </Stack>
        </Paper>
      </Container>
    );
  }

  if (error && !results) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button
          variant="outlined"
          startIcon={<ArrowBack />}
          onClick={() => navigate(`/applications/${applicationId}`)}
        >
          Back to Case
        </Button>
      </Container>
    );
  }

  if (!results) return null;

  const summary = results.summary || {};
  const findings = results.findings || [];

  // Group findings by severity/status
  const criticalFindings = findings.filter((f: any) =>
    ['critical', 'blocker', 'error'].includes(f.severity)
  );
  const warningFindings = findings.filter((f: any) => f.severity === 'warning');
  const needsReviewFindings = findings.filter((f: any) => f.status === 'needs_review');
  const infoFindings = findings.filter((f: any) => f.severity === 'info' && f.status !== 'needs_review');

  // Get unique documents
  const documents = results.documents || [];
  const hasReviewableFindings = needsReviewFindings.length > 0;

  const getSeverityIcon = (severity: string) => {
    if (['critical', 'blocker', 'error'].includes(severity)) return <Error color="error" />;
    if (severity === 'warning') return <Warning color="warning" />;
    return <Info color="info" />;
  };

  const handleDownloadReport = async () => {
    if (!runId) return;
    try {
      setDownloadingReport(true);
      const blob = await api.downloadReviewReport(parseInt(runId));
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `run-${runId}-hil-review-report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Failed to download report'));
    } finally {
      setDownloadingReport(false);
    }
  };

  const handleReclassifyDocument = async (documentId: number, documentName: string, isCorrect: boolean) => {
    if (!runId) return;
    
    const reclassifyKey = `${documentId}-${isCorrect}`;
    setReclassifying(reclassifyKey);
    setError('');
    
    try {
      // For thumbs up: keep the current document type (confirm correct)
      // For thumbs down: reclassify as 'incorrect' or 'other'
      const newType = isCorrect ? documentName : 'incorrect';
      
      await api.reclassifyDocument(parseInt(runId), documentId, newType);
      
      setSuccessMessage(`Document ${isCorrect ? 'confirmed' : 'marked as incorrect'}`);
      setTimeout(() => setSuccessMessage(''), 3000);
      
      // Refresh results to show updated candidate documents
      await loadResults(true);
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Failed to reclassify document'));
    } finally {
      setReclassifying(null);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {refreshing && <LinearProgress sx={{ mb: 2 }} />}
      {error && results && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage('')}>
          {successMessage}
        </Alert>
      )}
      {/* Header */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              📋 Run Results
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Run ID: #{runId}
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<ArrowBack />}
              onClick={() => navigate(`/applications/${applicationId}`)}
            >
              Back to Case
            </Button>
            {results.status === 'reviewed' && (
              <Button
                variant="contained"
                startIcon={<Description />}
                onClick={handleDownloadReport}
                disabled={downloadingReport}
              >
                {downloadingReport ? 'Preparing report...' : 'Download report'}
              </Button>
            )}
            {hasReviewableFindings && (
              <Button
                variant="contained"
                startIcon={<RateReview />}
                onClick={() => navigate(`/applications/${applicationId}/runs/${runId}/review`)}
              >
                Start Review
              </Button>
            )}
          </Stack>
        </Box>

        {/* Summary Stats */}
        <Grid container spacing={2} sx={{ mt: 2 }}>
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {summary.total_documents || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Documents
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="error.main">
                {criticalFindings.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Critical
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main">
                {warningFindings.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Warnings
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="info.main">
                {needsReviewFindings.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Needs Review
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Prior Approval Documents - Show if any PA rules are in findings */}
      {findings.some((f: any) => f.rule_id?.startsWith('PA-')) && results.submission_id && (
        <Box sx={{ mb: 3 }}>
          <PriorApprovalDocs
            runId={parseInt(runId!)}
            submissionId={results.submission_id}
            onUpdate={() => loadResults(true)}
          />
        </Box>
      )}

      {/* Documents List */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Documents
        </Typography>
        {documents.length === 0 ? (
          <Alert severity="info">No documents found</Alert>
        ) : (
          <List>
            {documents.map((doc: any, index: number) => (
              <ListItem
                key={index}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  mb: 1,
                }}
              >
                <Description sx={{ mr: 2, color: 'text.secondary' }} />
                <ListItemText
                  primary={doc.document_name || `Document ${index + 1}`}
                  secondary={doc.document_type || 'Unknown type'}
                />
                {doc.status === 'processed' && (
                  <CheckCircle color="success" sx={{ ml: 2 }} />
                )}
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      {/* Extracted Fields */}
      {results.extracted_fields && Object.keys(results.extracted_fields).length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Extracted Fields
          </Typography>
          <Box sx={{ pl: 2 }}>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '16px', 
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '0.875rem'
            }}>
              {JSON.stringify(results.extracted_fields, null, 2)}
            </pre>
          </Box>
        </Paper>
      )}

      {/* Critical Findings */}
      {criticalFindings.length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom color="error.main">
            Critical Issues ({criticalFindings.length})
          </Typography>
          <Stack spacing={2}>
            {criticalFindings.map((finding: any, index: number) => (
              <Box
                key={index}
                sx={{
                  p: 2,
                  border: '1px solid',
                  borderColor: 'error.main',
                  borderRadius: 1,
                  borderLeft: '4px solid',
                  borderLeftColor: 'error.main',
                  backgroundColor: 'error.lighter',
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                  {getSeverityIcon(finding.severity)}
                  <Chip label={finding.severity} color="error" size="small" />
                  <Chip label={finding.rule_id} size="small" variant="outlined" />
                  {finding.document_name && (
                    <Chip label={finding.document_name} size="small" icon={<Description />} />
                  )}
                </Box>
                <Typography variant="body1" gutterBottom>
                  {finding.message}
                </Typography>
                
                {/* Evidence Details */}
                {finding.evidence_details && finding.evidence_details.length > 0 && (
                  <Accordion sx={{ mt: 2, backgroundColor: 'rgba(255,255,255,0.7)' }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <FindInPage />
                        <Typography variant="subtitle2">
                          Evidence ({finding.evidence_details.length} items)
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Stack spacing={1}>
                        {finding.evidence_details.map((evidence: any, evIndex: number) => (
                          <Box
                            key={evIndex}
                            onClick={() => {
                              setSelectedDocument({
                                id: evidence.document_id,
                                name: evidence.document_name || `Document ${evidence.document_id}`,
                              });
                              setSelectedEvidence(evidence);
                              setViewerOpen(true);
                            }}
                            sx={{
                              p: 1.5,
                              backgroundColor: 'grey.50',
                              borderRadius: 1,
                              border: '1px solid',
                              borderColor: 'grey.300',
                              cursor: 'pointer',
                              transition: 'all 0.2s',
                              '&:hover': {
                                backgroundColor: 'primary.50',
                                borderColor: 'primary.main',
                                transform: 'translateX(4px)',
                              },
                            }}
                          >
                            <Typography variant="caption" color="text.secondary">
                              Page {evidence.page} {evidence.evidence_key && `• ${evidence.evidence_key}`}
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 0.5, fontFamily: 'monospace' }}>
                              "{evidence.snippet}"
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                              {evidence.confidence && (
                                <Chip
                                  label={`Confidence: ${(evidence.confidence * 100).toFixed(0)}%`}
                                  size="small"
                                />
                              )}
                              <Chip
                                icon={<FindInPage />}
                                label="View in document"
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            </Box>
                          </Box>
                        ))}
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Candidate Documents */}
                {finding.candidate_documents && finding.candidate_documents.length > 0 && (
                  <Accordion sx={{ mt: 1, backgroundColor: 'rgba(255,255,255,0.7)' }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <Description />
                        <Typography variant="subtitle2">
                          Possible Matches ({finding.candidate_documents.length})
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        Use 👍 to confirm a match or 👎 to flag an incorrect document.
                      </Typography>
                      <Stack spacing={1}>
                        {finding.candidate_documents.map((doc: any, docIndex: number) => (
                          <Box
                            key={docIndex}
                            sx={{
                              p: 1.5,
                              backgroundColor: doc.scanned ? 'success.lighter' : 'grey.100',
                              borderRadius: 1,
                              border: '1px solid',
                              borderColor: doc.scanned ? 'success.main' : 'grey.300',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <Box>
                              <Typography variant="body2" fontWeight="medium">
                                {doc.document_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {doc.reason}
                              </Typography>
                              {doc.confidence && (
                                <Chip
                                  label={`${(doc.confidence * 100).toFixed(0)}%`}
                                  size="small"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </Box>
                            <Box>
                              <Tooltip title="Confirm correct document">
                                <IconButton
                                  size="small"
                                  color="success"
                                  onClick={() => handleReclassifyDocument(
                                    doc.document_id,
                                    doc.document_name,
                                    true
                                  )}
                                  disabled={reclassifying === `${doc.document_id}-true`}
                                >
                                  <ThumbUp fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Mark as incorrect">
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => handleReclassifyDocument(
                                    doc.document_id,
                                    doc.document_name,
                                    false
                                  )}
                                  disabled={reclassifying === `${doc.document_id}-false`}
                                >
                                  <ThumbDown fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </Box>
                        ))}
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )}

                {finding.details && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {JSON.stringify(finding.details, null, 2)}
                  </Typography>
                )}
              </Box>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Warning Findings */}
      {warningFindings.length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom color="warning.main">
            Warnings ({warningFindings.length})
          </Typography>
          <Stack spacing={2}>
            {warningFindings.map((finding: any, index: number) => (
              <Box
                key={index}
                sx={{
                  p: 2,
                  border: '1px solid',
                  borderColor: 'warning.main',
                  borderRadius: 1,
                  borderLeft: '4px solid',
                  borderLeftColor: 'warning.main',
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                  {getSeverityIcon(finding.severity)}
                  <Chip label={finding.severity} color="warning" size="small" />
                  <Chip label={finding.rule_id} size="small" variant="outlined" />
                  {finding.document_name && (
                    <Chip label={finding.document_name} size="small" icon={<Description />} />
                  )}
                </Box>
                <Typography variant="body1" gutterBottom>
                  {finding.message}
                </Typography>
                
                {/* Evidence Details */}
                {finding.evidence_details && finding.evidence_details.length > 0 && (
                  <Accordion sx={{ mt: 2, backgroundColor: 'rgba(255,255,255,0.7)' }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <FindInPage />
                        <Typography variant="subtitle2">
                          Evidence ({finding.evidence_details.length} items)
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Stack spacing={1}>
                        {finding.evidence_details.map((evidence: any, evIndex: number) => (
                          <Box key={evIndex} sx={{ p: 1.5, backgroundColor: 'grey.50', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">
                              Page {evidence.page}
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 0.5 }}>
                              "{evidence.snippet}"
                            </Typography>
                          </Box>
                        ))}
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Candidate Documents */}
                {finding.candidate_documents && finding.candidate_documents.length > 0 && (
                  <Accordion sx={{ mt: 1, backgroundColor: 'rgba(255,255,255,0.7)' }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="subtitle2">
                        Possible Matches ({finding.candidate_documents.length})
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        Use 👍 to confirm a match or 👎 to flag an incorrect document.
                      </Typography>
                      <Stack spacing={1}>
                        {finding.candidate_documents.map((doc: any, docIndex: number) => (
                          <Box
                            key={docIndex}
                            sx={{
                              p: 1.5,
                              backgroundColor: doc.scanned ? 'success.lighter' : 'grey.100',
                              borderRadius: 1,
                              border: '1px solid',
                              borderColor: doc.scanned ? 'success.main' : 'grey.300',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <Box>
                              <Typography variant="body2" fontWeight="medium">
                                {doc.document_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {doc.reason}
                              </Typography>
                              {doc.confidence && (
                                <Chip
                                  label={`${(doc.confidence * 100).toFixed(0)}%`}
                                  size="small"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </Box>
                            <Box>
                              <Tooltip title="Confirm correct document">
                                <IconButton
                                  size="small"
                                  color="success"
                                  onClick={() => handleReclassifyDocument(
                                    doc.document_id,
                                    doc.document_name,
                                    true
                                  )}
                                  disabled={reclassifying === `${doc.document_id}-true`}
                                >
                                  <ThumbUp fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Mark as incorrect">
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => handleReclassifyDocument(
                                    doc.document_id,
                                    doc.document_name,
                                    false
                                  )}
                                  disabled={reclassifying === `${doc.document_id}-false`}
                                >
                                  <ThumbDown fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </Box>
                        ))}
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )}
              </Box>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Info Findings */}
      {infoFindings.length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom color="info.main">
            Informational ({infoFindings.length})
          </Typography>
          <Stack spacing={2}>
            {infoFindings.map((finding: any, index: number) => (
              <Box
                key={index}
                sx={{
                  p: 2,
                  border: '1px solid',
                  borderColor: 'info.main',
                  borderRadius: 1,
                  borderLeft: '4px solid',
                  borderLeftColor: 'info.main',
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                  {getSeverityIcon(finding.severity)}
                  <Chip label={finding.severity} color="info" size="small" />
                  <Chip label={finding.rule_id} size="small" variant="outlined" />
                  {finding.document_name && (
                    <Chip label={finding.document_name} size="small" icon={<Description />} />
                  )}
                </Box>
                <Typography variant="body1" gutterBottom>
                  {finding.message}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Needs Review Findings */}
      {needsReviewFindings.length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom color="info.main">
            Needs Human Review ({needsReviewFindings.length})
          </Typography>
          <Stack spacing={2}>
            {needsReviewFindings.map((finding: any, index: number) => (
              <Box
                key={index}
                sx={{
                  p: 2,
                  border: '1px solid',
                  borderColor: 'info.main',
                  borderRadius: 1,
                  borderLeft: '4px solid',
                  borderLeftColor: 'info.main',
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                  {getSeverityIcon(finding.severity)}
                  <Chip label={finding.severity} color="info" size="small" />
                  <Chip label={finding.rule_id} size="small" variant="outlined" />
                  {finding.document_name && (
                    <Chip label={finding.document_name} size="small" icon={<Description />} />
                  )}
                </Box>
                <Typography variant="body1" gutterBottom>
                  {finding.message}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Paper>
      )}

      {findings.length === 0 && (
        <Alert severity="success" icon={<CheckCircle />}>
          ✅ No issues found - all validation checks passed!
        </Alert>
      )}

      {/* LLM Transparency Section */}
      {runId && (
        <Box sx={{ mt: 3 }}>
          <LLMTransparency runId={parseInt(runId)} />
        </Box>
      )}

      {/* Document Viewer Dialog */}
      <DocumentViewer
        open={viewerOpen}
        onClose={() => {
          setViewerOpen(false);
          setSelectedDocument(null);
          setSelectedEvidence(null);
        }}
        documentId={selectedDocument?.id}
        documentName={selectedDocument?.name}
        initialPage={selectedEvidence?.page}
        evidence={selectedEvidence}
        runId={runId ? parseInt(runId) : undefined}
      />
    </Container>
  );
}
