import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Alert,
  Button,
  Stack,
  List,
  ListItem,
  ListItemText,
  Paper,
  Container,
  Skeleton,
  LinearProgress,
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
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Assignment sx={{ fontSize: 32, color: 'primary.main' }} />
              <Typography variant="h4">
                Run Results
              </Typography>
            </Box>
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

      {/* Extracted Fields - NEW UX */}
      {results.extracted_fields && Object.keys(results.extracted_fields).length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
            <FindInPage />
            Extracted Fields ({Object.keys(results.extracted_fields).length})
          </Typography>
          <ExtractedFieldsDisplay extractedFields={results.extracted_fields} />
        </Paper>
      )}

      {/* Validation Findings - NEW UX (Replaces all old findings sections) */}
      <ValidationFindingsDisplay 
        findings={findings}
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
