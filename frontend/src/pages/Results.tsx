import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Button,
  Divider,
  Stack,
  List,
  ListItem,
  ListItemText,
  Paper,
  Container,
} from '@mui/material';
import {
  RateReview,
  ArrowBack,
  Description,
  Error,
  Warning,
  Info,
  CheckCircle,
} from '@mui/icons-material';
import { api } from '../api/client';

interface FindingsByDocument {
  [documentName: string]: any[];
}

export default function Results() {
  const { applicationId, runId } = useParams<{ applicationId: string; runId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadResults = async () => {
    if (!runId) return;
    
    setLoading(true);
    setError('');
    try {
      const data = await api.getRunResults(parseInt(runId));
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load results');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResults();
  }, [runId]);

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

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
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
                  primary={doc.document_name || doc.filename || `Document ${index + 1}`}
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
                {finding.details && (
                  <Typography variant="body2" color="text.secondary">
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
    </Container>
  );
}
