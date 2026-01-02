import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  Alert,
  CircularProgress,
  TextField,
} from '@mui/material';
import { api } from '../api/client';

export default function Results() {
  const { runId } = useParams<{ runId: string }>();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [inputRunId, setInputRunId] = useState(runId || '');

  const loadResults = async (id: string) => {
    if (!id) return;
    
    setLoading(true);
    setError('');
    try {
      const data = await api.getRunResults(parseInt(id));
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load results');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (runId) {
      loadResults(runId);
    } else {
      setLoading(false);
    }
  }, [runId]);

  if (!runId && !inputRunId) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom fontWeight="bold">
          📋 Validation Results
        </Typography>
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" gutterBottom>
              Enter Run ID
            </Typography>
            <Box sx={{ maxWidth: 400, mx: 'auto', mt: 3 }}>
              <TextField
                fullWidth
                label="Run ID"
                value={inputRunId}
                onChange={(e) => setInputRunId(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    loadResults(inputRunId);
                  }
                }}
              />
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!results) return null;

  const summary = results.summary || {};
  const findings = results.findings || [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight="bold">
        📋 Validation Results
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Run ID: {runId || inputRunId}
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3, mt: 1 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="primary">
                {summary.total_documents || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Documents
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="success.main">
                {summary.processed || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Processed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="error.main">
                {summary.errors || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Errors
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="info.main">
                {results.llm_calls_per_run || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                LLM Calls
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Validation Findings */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Validation Findings
          </Typography>
          {findings.length === 0 ? (
            <Alert severity="success">✅ No issues found</Alert>
          ) : (
            findings.map((finding: any, index: number) => (
              <Box
                key={index}
                sx={{
                  p: 2,
                  mb: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  borderLeft: `4px solid ${
                    finding.severity === 'blocker' || finding.severity === 'critical'
                      ? '#f44336'
                      : finding.severity === 'warning'
                      ? '#ff9800'
                      : '#2196f3'
                  }`,
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                  <Chip
                    label={finding.severity}
                    color={
                      finding.severity === 'blocker' || finding.severity === 'critical'
                        ? 'error'
                        : finding.severity === 'warning'
                        ? 'warning'
                        : 'info'
                    }
                    size="small"
                  />
                  <Chip label={finding.rule_id} size="small" variant="outlined" />
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
            ))
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
