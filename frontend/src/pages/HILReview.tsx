import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Stack,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
  TextField,
  CircularProgress,
  Alert,
  LinearProgress,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  HelpOutline,
  ArrowBack,
  NavigateNext,
  NavigateBefore,
  Close,
  Save,
} from '@mui/icons-material';
import { api } from '../api/client';

const DRAWER_WIDTH = 300;

interface Finding {
  id: number;
  rule_id: string;
  severity: string;
  message: string;
  document_name?: string;
  details?: any;
  decision?: string;
  comment?: string;
}

interface ReviewStatus {
  total_findings: number;
  reviewed_count: number;
  pending_count: number;
  accept_count: number;
  reject_count: number;
  need_info_count: number;
}

const HILReview: React.FC = () => {
  const { applicationId, runId } = useParams<{ applicationId: string; runId: string }>();
  const navigate = useNavigate();
  
  const [findings, setFindings] = useState<Finding[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | null>(null);
  const [showCompleteDialog, setShowCompleteDialog] = useState(false);

  useEffect(() => {
    loadReviewData();
  }, [runId]);

  const loadReviewData = async () => {
    if (!runId) return;

    try {
      setLoading(true);
      setError('');
      
      // Load run results to get findings
      const results = await api.getRunResults(parseInt(runId));
      const reviewableFindings = (results.findings || []).filter(
        (f: any) => f.severity === 'info' || f.severity === 'needs_review'
      );
      setFindings(reviewableFindings);

      // Load review status
      const status = await api.getReviewStatus(parseInt(runId));
      setReviewStatus(status);
    } catch (err: any) {
      console.error('Failed to load review data:', err);
      setError(err.message || 'Failed to load review data');
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (decision: 'accept' | 'reject' | 'need_info') => {
    const currentFinding = findings[currentIndex];
    if (!currentFinding || !runId) return;

    try {
      setSubmitting(true);
      await api.submitReviewDecision(
        parseInt(runId),
        currentFinding.id,
        decision,
        comment
      );

      // Update local state
      const updatedFindings = [...findings];
      updatedFindings[currentIndex] = {
        ...currentFinding,
        decision,
        comment,
      };
      setFindings(updatedFindings);

      // Reload review status
      const status = await api.getReviewStatus(parseInt(runId));
      setReviewStatus(status);

      // Clear comment and move to next finding
      setComment('');
      if (currentIndex < findings.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (err: any) {
      console.error('Failed to submit decision:', err);
      setError(err.message || 'Failed to submit decision');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompleteReview = async () => {
    if (!runId) return;

    try {
      setSubmitting(true);
      await api.completeReview(parseInt(runId));
      setShowCompleteDialog(false);
      
      // Navigate back to application details
      navigate(`/applications/${applicationId}`, {
        state: { message: 'Review completed successfully!' },
      });
    } catch (err: any) {
      console.error('Failed to complete review:', err);
      setError(err.message || 'Failed to complete review');
    } finally {
      setSubmitting(false);
    }
  };

  const getDecisionColor = (decision?: string) => {
    if (decision === 'accept') return 'success';
    if (decision === 'reject') return 'error';
    if (decision === 'need_info') return 'warning';
    return 'default';
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
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}
          >
            Back to Results
          </Button>
        </Box>
      </Container>
    );
  }

  if (findings.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="info">
          No findings require human review for this run.
        </Alert>
        <Box sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}
          >
            Back to Results
          </Button>
        </Box>
      </Container>
    );
  }

  const currentFinding = findings[currentIndex];
  const progress = reviewStatus
    ? (reviewStatus.reviewed_count / reviewStatus.total_findings) * 100
    : 0;

  return (
    <Box sx={{ display: 'flex' }}>
      {/* Sidebar Navigation */}
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            position: 'relative',
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Findings ({findings.length})
          </Typography>
          <LinearProgress variant="determinate" value={progress} sx={{ mb: 2 }} />
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {reviewStatus?.reviewed_count || 0} / {reviewStatus?.total_findings || 0} reviewed
          </Typography>
        </Box>
        <Divider />
        <List sx={{ overflow: 'auto', flexGrow: 1 }}>
          {findings.map((finding, index) => (
            <ListItem key={finding.id} disablePadding>
              <ListItemButton
                selected={index === currentIndex}
                onClick={() => setCurrentIndex(index)}
              >
                <Box sx={{ width: '100%' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight={index === currentIndex ? 'bold' : 'normal'}>
                      Finding #{index + 1}
                    </Typography>
                    {finding.decision && (
                      <Chip
                        label={finding.decision}
                        size="small"
                        color={getDecisionColor(finding.decision)}
                      />
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {finding.rule_id}
                  </Typography>
                </Box>
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Divider />
        <Box sx={{ p: 2 }}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}
            sx={{ mb: 1 }}
          >
            Back to Results
          </Button>
          <Button
            fullWidth
            variant="contained"
            color="success"
            startIcon={<Save />}
            onClick={() => setShowCompleteDialog(true)}
            disabled={reviewStatus?.pending_count !== 0}
          >
            Complete Review
          </Button>
          {reviewStatus && reviewStatus.pending_count > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              {reviewStatus.pending_count} finding(s) still pending
            </Typography>
          )}
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Container maxWidth="md">
          {/* Header */}
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h5">
                Finding {currentIndex + 1} of {findings.length}
              </Typography>
              <Stack direction="row" spacing={1}>
                <IconButton
                  onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                  disabled={currentIndex === 0}
                >
                  <NavigateBefore />
                </IconButton>
                <IconButton
                  onClick={() => setCurrentIndex(Math.min(findings.length - 1, currentIndex + 1))}
                  disabled={currentIndex === findings.length - 1}
                >
                  <NavigateNext />
                </IconButton>
              </Stack>
            </Box>
          </Paper>

          {/* Finding Details */}
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Stack spacing={2}>
              <Box>
                <Chip label={currentFinding.severity} color="info" size="small" sx={{ mr: 1 }} />
                <Chip label={currentFinding.rule_id} size="small" variant="outlined" />
                {currentFinding.document_name && (
                  <Chip label={currentFinding.document_name} size="small" sx={{ ml: 1 }} />
                )}
              </Box>

              <Typography variant="h6">Message</Typography>
              <Typography variant="body1">{currentFinding.message}</Typography>

              {currentFinding.details && (
                <>
                  <Typography variant="h6">Details</Typography>
                  <Box
                    sx={{
                      p: 2,
                      backgroundColor: '#f5f5f5',
                      borderRadius: 1,
                      overflow: 'auto',
                    }}
                  >
                    <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                      {JSON.stringify(currentFinding.details, null, 2)}
                    </pre>
                  </Box>
                </>
              )}

              {currentFinding.decision && (
                <Alert
                  severity={
                    currentFinding.decision === 'accept'
                      ? 'success'
                      : currentFinding.decision === 'reject'
                      ? 'error'
                      : 'warning'
                  }
                >
                  Already reviewed: <strong>{currentFinding.decision}</strong>
                  {currentFinding.comment && <Box sx={{ mt: 1 }}>Comment: {currentFinding.comment}</Box>}
                </Alert>
              )}
            </Stack>
          </Paper>

          {/* Decision Form */}
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Your Decision
            </Typography>

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Comment (optional)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add any notes or reasoning for your decision..."
              sx={{ mb: 3 }}
              disabled={submitting}
            />

            <Stack direction="row" spacing={2} justifyContent="center">
              <Button
                variant="contained"
                color="success"
                size="large"
                startIcon={<CheckCircle />}
                onClick={() => handleDecision('accept')}
                disabled={submitting}
                sx={{ minWidth: 140 }}
              >
                Accept
              </Button>
              <Button
                variant="contained"
                color="error"
                size="large"
                startIcon={<Cancel />}
                onClick={() => handleDecision('reject')}
                disabled={submitting}
                sx={{ minWidth: 140 }}
              >
                Reject
              </Button>
              <Button
                variant="contained"
                color="warning"
                size="large"
                startIcon={<HelpOutline />}
                onClick={() => handleDecision('need_info')}
                disabled={submitting}
                sx={{ minWidth: 140 }}
              >
                Need Info
              </Button>
            </Stack>

            {submitting && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}
          </Paper>
        </Container>
      </Box>

      {/* Complete Review Dialog */}
      <Dialog open={showCompleteDialog} onClose={() => setShowCompleteDialog(false)}>
        <DialogTitle>Complete Review</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to complete this review? All {reviewStatus?.reviewed_count || 0}{' '}
            findings have been reviewed.
          </Typography>
          {reviewStatus && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2">
                • Accepted: {reviewStatus.accept_count}
              </Typography>
              <Typography variant="body2">
                • Rejected: {reviewStatus.reject_count}
              </Typography>
              <Typography variant="body2">
                • Need Info: {reviewStatus.need_info_count}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCompleteDialog(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={handleCompleteReview}
            variant="contained"
            color="success"
            disabled={submitting}
          >
            {submitting ? <CircularProgress size={24} /> : 'Complete Review'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default HILReview;
