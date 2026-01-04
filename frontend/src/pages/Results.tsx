import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Alert,
  AlertTitle,
  Button,
  Stack,
  List,
  ListItem,
  ListItemText,
  Paper,
  Container,
  Skeleton,
  LinearProgress,
  Chip,
} from '@mui/material';
import {
  RateReview,
  ArrowBack,
  Description,
  CheckCircle,
  FindInPage,
  Assignment,
} from '@mui/icons-material';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errorUtils';
import DocumentViewer from '../components/DocumentViewer';
import LLMTransparency from '../components/LLMTransparency';
import PriorApprovalDocs from '../components/PriorApprovalDocs';
import ExtractedFieldsDisplay from '../components/ExtractedFieldsDisplay';
import ValidationFindingsDisplay from '../components/ValidationFindingsDisplay';

export default function Results() {
  const { applicationId, runId } = useParams<{ applicationId: string; runId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [viewerOpen, setViewerOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<any>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);
  const [runStatus, setRunStatus] = useState<string>('');
  const [processingProgress, setProcessingProgress] = useState<number>(0);

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
      setRunStatus(data.status || 'completed');
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
        const parsed = JSON.parse(cachedResults);
        setResults(parsed);
        setRunStatus(parsed.status || 'completed');
        setLoading(false);
      } catch (err) {
        console.warn('Failed to parse cached run results:', err);
      }
    }
    loadResults(Boolean(cachedResults));
  }, [runId]);

  // Auto-refresh when processing
  useEffect(() => {
    if (!runId || !runStatus) return;

    const isProcessing = ['pending', 'running'].includes(runStatus);
    if (!isProcessing) return;

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProcessingProgress(prev => {
        if (prev >= 90) return 90; // Cap at 90% until actually complete
        return prev + Math.random() * 10;
      });
    }, 2000);

    // Poll for status updates
    const pollInterval = setInterval(() => {
      loadResults(true);
    }, 5000); // Check every 5 seconds

    return () => {
      clearInterval(progressInterval);
      clearInterval(pollInterval);
    };
  }, [runId, runStatus]);

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
  const isProcessing = ['pending', 'running'].includes(runStatus);

  // Group findings by severity for stats display
  const criticalFindings = findings.filter((f: any) =>
    ['critical', 'blocker', 'error'].includes(f.severity?.toLowerCase())
  );
  const warningFindings = findings.filter((f: any) => f.severity?.toLowerCase() === 'warning');
  const needsReviewFindings = findings.filter((f: any) => f.status === 'needs_review');
  const infoFindings = findings.filter((f: any) => f.severity?.toLowerCase() === 'info');

  // Get unique documents
  const documents = results.documents || [];
  const hasReviewableFindings = needsReviewFindings.length > 0;

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

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Processing Status Banner */}
      {isProcessing && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <AlertTitle>Processing Documents...</AlertTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {runStatus === 'pending' ? 'Waiting to start processing...' : 'Extracting text and validating documents...'}
              </Typography>
              <LinearProgress variant="determinate" value={processingProgress} />
            </Box>
            <Typography variant="caption" color="text.secondary">
              {Math.round(processingProgress)}%
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            This page will automatically refresh when processing is complete.
          </Typography>
        </Alert>
      )}

      {refreshing && !isProcessing && <LinearProgress sx={{ mb: 2 }} />}
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
      <Paper elevation={3} sx={{ p: 4, mb: 3, bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
              <Assignment sx={{ fontSize: 40, color: 'primary.main' }} />
              <Typography variant="h3" sx={{ fontWeight: 700 }}>
                Validation Results
              </Typography>
            </Box>
            <Typography variant="body1" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Run #{runId} •
              <Chip
                label={runStatus}
                size="small"
                color={isProcessing ? 'warning' : 'success'}
                sx={{ fontWeight: 600 }}
              />
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<ArrowBack />}
              onClick={() => navigate(`/applications/${applicationId}`)}
              size="large"
            >
              Back to Case
            </Button>
            {results.status === 'reviewed' && (
              <Button
                variant="contained"
                startIcon={<Description />}
                onClick={handleDownloadReport}
                disabled={downloadingReport}
                size="large"
              >
                {downloadingReport ? 'Preparing...' : 'Download Report'}
              </Button>
            )}
            {hasReviewableFindings && (
              <Button
                variant="contained"
                color="warning"
                startIcon={<RateReview />}
                onClick={() => navigate(`/applications/${applicationId}/runs/${runId}/review`)}
                size="large"
                sx={{ fontWeight: 600 }}
              >
                Start Review
              </Button>
            )}
          </Stack>
        </Box>

        {/* Summary Stats - Enhanced with better visuals */}
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={6} md={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                textAlign: 'center',
                bgcolor: 'primary.lighter',
                border: '2px solid',
                borderColor: 'primary.main',
                borderRadius: 2,
              }}
            >
              <Typography variant="h3" color="primary.main" sx={{ fontWeight: 700, mb: 0.5 }}>
                {summary.total_documents || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Documents Processed
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6} md={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                textAlign: 'center',
                bgcolor: criticalFindings.length > 0 ? 'error.lighter' : 'grey.50',
                border: '2px solid',
                borderColor: criticalFindings.length > 0 ? 'error.main' : 'grey.300',
                borderRadius: 2,
              }}
            >
              <Typography
                variant="h3"
                color={criticalFindings.length > 0 ? 'error.main' : 'text.secondary'}
                sx={{ fontWeight: 700, mb: 0.5 }}
              >
                {criticalFindings.length}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Critical Issues
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6} md={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                textAlign: 'center',
                bgcolor: warningFindings.length > 0 ? 'warning.lighter' : 'grey.50',
                border: '2px solid',
                borderColor: warningFindings.length > 0 ? 'warning.main' : 'grey.300',
                borderRadius: 2,
              }}
            >
              <Typography
                variant="h3"
                color={warningFindings.length > 0 ? 'warning.main' : 'text.secondary'}
                sx={{ fontWeight: 700, mb: 0.5 }}
              >
                {warningFindings.length}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Warnings
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6} md={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                textAlign: 'center',
                bgcolor: needsReviewFindings.length > 0 ? 'info.lighter' : 'grey.50',
                border: '2px solid',
                borderColor: needsReviewFindings.length > 0 ? 'info.main' : 'grey.300',
                borderRadius: 2,
              }}
            >
              <Typography
                variant="h3"
                color={needsReviewFindings.length > 0 ? 'info.main' : 'text.secondary'}
                sx={{ fontWeight: 700, mb: 0.5 }}
              >
                {needsReviewFindings.length}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Needs Review
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Quick Summary Message */}
        {findings.length > 0 && (
          <Alert
            severity={criticalFindings.length > 0 ? 'error' : warningFindings.length > 0 ? 'warning' : 'success'}
            sx={{ mt: 3 }}
          >
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {criticalFindings.length > 0
                ? `⚠️ ${criticalFindings.length} critical ${criticalFindings.length === 1 ? 'issue requires' : 'issues require'} immediate attention`
                : warningFindings.length > 0
                ? `✓ No critical issues found, but ${warningFindings.length} ${warningFindings.length === 1 ? 'warning needs' : 'warnings need'} review`
                : '✅ All validation checks passed successfully!'}
            </Typography>
          </Alert>
        )}
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
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Description color="primary" />
          Submitted Documents
          <Chip label={documents.length} size="small" color="primary" />
        </Typography>
        {documents.length === 0 ? (
          <Alert severity="info">No documents found</Alert>
        ) : (
          <Grid container spacing={2}>
            {documents.map((doc: any, index: number) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    transition: 'all 0.2s',
                    '&:hover': {
                      boxShadow: 2,
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  <Description sx={{ fontSize: 32, color: 'primary.main' }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {doc.document_name || `Document ${index + 1}`}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {doc.document_type || 'Unknown type'}
                    </Typography>
                  </Box>
                  {doc.status === 'processed' && (
                    <CheckCircle color="success" sx={{ fontSize: 28 }} />
                  )}
                </Paper>
              </Grid>
            ))}
          </Grid>
        )}
      </Paper>

      {/* Extracted Fields - NEW UX */}
      {results.extracted_fields && Object.keys(results.extracted_fields).length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FindInPage color="primary" />
            Extracted Information
            <Chip label={`${Object.keys(results.extracted_fields).length} fields`} size="small" color="primary" />
          </Typography>
          <ExtractedFieldsDisplay extractedFields={results.extracted_fields} />
        </Paper>
      )}

      {/* Validation Findings - NEW UX (Replaces all old findings sections) */}
      <ValidationFindingsDisplay
        findings={findings}
        runId={runId ? parseInt(runId) : undefined}
        applicationId={applicationId ? parseInt(applicationId) : undefined}
        onViewDocument={(documentId, evidenceDetails) => {
          setSelectedDocument({
            id: documentId,
            name: evidenceDetails?.document_name || `Document ${documentId}`,
          });
          setSelectedEvidence(evidenceDetails);
          setViewerOpen(true);
        }}
      />

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
