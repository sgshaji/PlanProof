import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Container, Paper, Typography, Button, CircularProgress, Alert,
  Stack, Chip, Box, TextField, LinearProgress, Divider, List,
  ListItem, ListItemButton, ListItemText, ListItemIcon, Snackbar
} from '@mui/material';
import { 
  ArrowBack, CheckCircle, Cancel, HelpOutline, 
  NavigateBefore, NavigateNext, Done, Schedule,
  Warning, Error as ErrorIcon, Info, Download
} from '@mui/icons-material';
import { api } from '../api/client';

interface Finding {
  id: number;
  rule_id: string;
  severity: string;
  message: string;
  status: string;
  decision?: string;
  comment?: string;
  document_name?: string;
  details?: Record<string, any>;
}

const HILReview: React.FC = () => {
  const { applicationId, runId } = useParams<{ applicationId: string; runId: string }>();
  const navigate = useNavigate();
  
  const [findings, setFindings] = useState<Finding[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [comment, setComment] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    loadData();
  }, [runId]);

  const loadData = async () => {
    if (!runId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const results = await api.getRunResults(parseInt(runId));
      
      const reviewable = (results.findings || []).filter(
        (f: any) => f.status === 'needs_review'
      );
      setFindings(reviewable);
    } catch (err: any) {
      setError(err.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (decision: 'accept' | 'reject' | 'need_info') => {
    const finding = findings[currentIndex];
    if (!finding || !runId) return;

    try {
      setSubmitting(true);
      await api.submitReviewDecision(parseInt(runId), finding.id, decision, comment);
      
      // Update local state
      const updated = [...findings];
      updated[currentIndex] = { ...finding, decision, comment };
      setFindings(updated);
      
      setSuccessMessage(`Finding marked as ${decision.replace('_', ' ')}`);
      setComment(''); // Clear comment after submission
      
      // Move to next unreviewed if available
      const nextUnreviewed = updated.findIndex((f, i) => i > currentIndex && !f.decision);
      if (nextUnreviewed !== -1) {
        setCurrentIndex(nextUnreviewed);
      } else if (currentIndex < findings.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompleteReview = async () => {
    if (!runId) return;
    try {
      await api.completeReview(parseInt(runId));
      setSuccessMessage('Review completed successfully!');
      setTimeout(() => {
        navigate(`/applications/${applicationId}/runs/${runId}`);
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to complete review');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'error':
      case 'critical': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'error':
      case 'critical': return <ErrorIcon fontSize="small" />;
      case 'warning': return <Warning fontSize="small" />;
      default: return <Info fontSize="small" />;
    }
  };

  const getDecisionIcon = (decision?: string) => {
    switch (decision) {
      case 'accept': return <CheckCircle color="success" fontSize="small" />;
      case 'reject': return <Cancel color="error" fontSize="small" />;
      case 'need_info': return <HelpOutline color="warning" fontSize="small" />;
      default: return <Schedule color="disabled" fontSize="small" />;
    }
  };

  // Stats
  const reviewedCount = findings.filter(f => f.decision).length;
  const pendingCount = findings.length - reviewedCount;
  const acceptCount = findings.filter(f => f.decision === 'accept').length;
  const rejectCount = findings.filter(f => f.decision === 'reject').length;
  const needInfoCount = findings.filter(f => f.decision === 'need_info').length;
  const progress = findings.length > 0 ? (reviewedCount / findings.length) * 100 : 0;

  // Loading
  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }} color="text.secondary">Loading review data...</Typography>
      </Container>
    );
  }

  // Error
  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" onClose={() => setError('')}>{error}</Alert>
        <Button sx={{ mt: 2 }} startIcon={<ArrowBack />}
          onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}>
          Back
        </Button>
      </Container>
    );
  }

  // No findings
  if (findings.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Done sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>All Clear!</Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            No findings require human review for this validation run.
          </Typography>
          <Button variant="contained" startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}>
            Back to Results
          </Button>
        </Paper>
      </Container>
    );
  }

  const currentFinding = findings[currentIndex];
  const allReviewed = pendingCount === 0;

  return (
    <Box sx={{ display: 'flex', gap: 3, p: 3, minHeight: 'calc(100vh - 128px)' }}>
      {/* Left Sidebar - Findings List */}
      <Paper sx={{ width: 280, flexShrink: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white' }}>
          <Typography variant="h6">Findings</Typography>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            {reviewedCount} of {findings.length} reviewed
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ mt: 1, bgcolor: 'rgba(255,255,255,0.2)', '& .MuiLinearProgress-bar': { bgcolor: 'white' } }}
          />
        </Box>
        
        {/* Stats */}
        <Box sx={{ p: 2, display: 'flex', gap: 1, flexWrap: 'wrap', borderBottom: 1, borderColor: 'divider' }}>
          <Chip size="small" icon={<Schedule />} label={`${pendingCount} pending`} />
          <Chip size="small" icon={<CheckCircle />} label={acceptCount} color="success" variant="outlined" />
          <Chip size="small" icon={<Cancel />} label={rejectCount} color="error" variant="outlined" />
          <Chip size="small" icon={<HelpOutline />} label={needInfoCount} color="warning" variant="outlined" />
        </Box>

        <List sx={{ overflow: 'auto', flexGrow: 1 }}>
          {findings.map((finding, idx) => (
            <ListItem key={finding.id} disablePadding>
              <ListItemButton 
                selected={idx === currentIndex}
                onClick={() => setCurrentIndex(idx)}
                sx={{ py: 1 }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {getDecisionIcon(finding.decision)}
                </ListItemIcon>
                <ListItemText 
                  primary={`#${idx + 1} ${finding.rule_id}`}
                  secondary={finding.message.slice(0, 30) + '...'}
                  primaryTypographyProps={{ variant: 'body2', fontWeight: idx === currentIndex ? 'bold' : 'normal' }}
                  secondaryTypographyProps={{ variant: 'caption', noWrap: true }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider />
        <Box sx={{ p: 2 }}>
          <Button 
            fullWidth 
            variant="contained" 
            color="success"
            disabled={!allReviewed}
            onClick={handleCompleteReview}
            startIcon={<Done />}
            sx={{ mb: 1 }}
          >
            Complete Review
          </Button>
          <Button 
            fullWidth 
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}
          >
            Back to Results
          </Button>
        </Box>
      </Paper>

      {/* Main Content */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* Header */}
        <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h5">HIL Review</Typography>
            <Typography variant="body2" color="text.secondary">
              Application #{applicationId} • Run #{runId}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              variant="outlined"
              size="small"
              startIcon={<NavigateBefore />}
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex(currentIndex - 1)}
            >
              Previous
            </Button>
            <Chip label={`${currentIndex + 1} / ${findings.length}`} />
            <Button
              variant="outlined"
              size="small"
              endIcon={<NavigateNext />}
              disabled={currentIndex >= findings.length - 1}
              onClick={() => setCurrentIndex(currentIndex + 1)}
            >
              Next
            </Button>
          </Stack>
        </Paper>

        {/* Finding Card */}
        <Paper sx={{ p: 3, flexGrow: 1 }}>
          {/* Finding Header */}
          <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap', alignItems: 'center' }}>
            <Chip 
              label={currentFinding.rule_id} 
              color="primary" 
              icon={getSeverityIcon(currentFinding.severity)}
            />
            <Chip 
              label={currentFinding.severity} 
              color={getSeverityColor(currentFinding.severity) as any}
              variant="outlined"
            />
            {currentFinding.document_name && (
              <Chip label={currentFinding.document_name} size="small" variant="outlined" />
            )}
            {currentFinding.decision && (
              <Chip 
                label={currentFinding.decision.replace('_', ' ').toUpperCase()} 
                color={currentFinding.decision === 'accept' ? 'success' : currentFinding.decision === 'reject' ? 'error' : 'warning'}
                icon={getDecisionIcon(currentFinding.decision)}
              />
            )}
          </Box>

          {/* Issue */}
          <Typography variant="overline" color="text.secondary">Issue</Typography>
          <Typography variant="h6" sx={{ mb: 3 }}>{currentFinding.message}</Typography>

          {/* Details if available */}
          {currentFinding.details && Object.keys(currentFinding.details).length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="overline" color="text.secondary">Details</Typography>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50', mt: 1 }}>
                <pre style={{ margin: 0, fontSize: '0.85rem', overflow: 'auto' }}>
                  {JSON.stringify(currentFinding.details, null, 2)}
                </pre>
              </Paper>
            </Box>
          )}

          <Divider sx={{ my: 3 }} />

          {/* Comment Field */}
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Reviewer Notes (optional)"
            placeholder="Add any notes or reasoning for your decision..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={submitting}
            sx={{ mb: 3 }}
          />

          {/* Decision Buttons */}
          <Stack direction="row" spacing={2} justifyContent="center">
            <Button
              variant="contained"
              color="success"
              size="large"
              startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <CheckCircle />}
              onClick={() => handleDecision('accept')}
              disabled={submitting}
              sx={{ minWidth: 140, py: 1.5 }}
            >
              Accept
            </Button>
            <Button
              variant="contained"
              color="error"
              size="large"
              startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <Cancel />}
              onClick={() => handleDecision('reject')}
              disabled={submitting}
              sx={{ minWidth: 140, py: 1.5 }}
            >
              Reject
            </Button>
            <Button
              variant="contained"
              color="warning"
              size="large"
              startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <HelpOutline />}
              onClick={() => handleDecision('need_info')}
              disabled={submitting}
              sx={{ minWidth: 140, py: 1.5 }}
            >
              Need Info
            </Button>
          </Stack>

          {/* Previous Decision */}
          {currentFinding.decision && currentFinding.comment && (
            <Alert severity="info" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Previous note:</strong> {currentFinding.comment}
              </Typography>
            </Alert>
          )}
        </Paper>
      </Box>

      {/* Success Snackbar */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={3000}
        onClose={() => setSuccessMessage('')}
        message={successMessage}
      />
    </Box>
  );
};

export default HILReview;
