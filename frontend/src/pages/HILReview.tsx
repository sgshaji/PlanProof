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
  Save,
} from '@mui/icons-material';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errorUtils';
import LLMCallTracker from '../components/LLMCallTracker';
import { announceToScreenReader } from '../utils/accessibility';

const DRAWER_WIDTH = 280;
const LAYOUT_DRAWER_WIDTH = 240; // Width of the parent Layout drawer

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

interface LLMCall {
  timestamp: string;
  purpose: string;
  rule_type: string;
  tokens_used: number;
  model: string;
  response_time_ms: number;
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
  const [hasReviewPermission, setHasReviewPermission] = useState(true);
  const [llmCalls, setLlmCalls] = useState<LLMCall[]>([]);
  const [totalCalls, setTotalCalls] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);

  useEffect(() => {
    loadReviewData();
    checkUserPermission();
  }, [runId]);

  const loadReviewData = async () => {
    // Early return if no runId - must set loading to false to avoid stuck spinner
    if (!runId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      // Load run results to get findings
      const results = await api.getRunResults(parseInt(runId));
      console.log('HILReview: Loaded results:', results);
      console.log('HILReview: All findings:', results.findings);
      
      const reviewableFindings = (results.findings || []).filter(
        (f: any) => {
          console.log('HILReview: Checking finding:', f.rule_id, 'status:', f.status, 'match:', f.status === 'needs_review');
          return f.status === 'needs_review';
        }
      );
      console.log('HILReview: Reviewable findings (needs_review):', reviewableFindings);
      console.log('HILReview: Reviewable findings count:', reviewableFindings.length);
      setFindings(reviewableFindings);

      // Load review status
      const status = await api.getReviewStatus(parseInt(runId));
      console.log('HILReview: Review status:', status);
      setReviewStatus(status);
      
      const llmCallData = Array.isArray(results.llm_calls) ? results.llm_calls : [];
      setLlmCalls(llmCallData);
      const totals = results.llm_call_totals || {};
      const computedTokens = llmCallData.reduce(
        (sum: number, call: LLMCall) => sum + (call.tokens_used || 0),
        0
      );
      setTotalCalls(totals.total_calls ?? llmCallData.length);
      setTotalTokens(totals.total_tokens ?? computedTokens);
      
      console.log('HILReview: Load complete. Setting loading to false.');
    } catch (err: any) {
      console.error('Failed to load review data:', err);
      console.error('Error details:', err.response?.data, err.message);
      setError(getApiErrorMessage(err, 'Failed to load review data'));
    } finally {
      console.log('HILReview: Finally block - setting loading to false');
      setLoading(false);
    }
  };

  const checkUserPermission = async () => {
    try {
      const userInfo = await api.getCurrentUser();
      const allowedRoles = ['officer', 'admin', 'reviewer', 'planner'];
      const hasPermission = allowedRoles.includes(userInfo.role);
      setHasReviewPermission(hasPermission);
      if (!hasPermission) {
        announceToScreenReader('You do not have permission to review findings', 'assertive');
      }
    } catch (err) {
      console.error('Failed to check user permission:', err);
      // Default to true to avoid blocking the UI
      setHasReviewPermission(true);
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
      
      // Announce to screen readers
      announceToScreenReader(`Finding ${decision} successfully`);

      // Clear comment and move to next finding
      setComment('');
      if (currentIndex < findings.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (err: any) {
      console.error('Failed to submit decision:', err);
      setError(getApiErrorMessage(err, 'Failed to submit decision'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!runId) return;

    try {
      announceToScreenReader('Downloading review report...', 'polite');
      const blob = await api.downloadReviewReport(parseInt(runId));
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `review_report_${runId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      announceToScreenReader('Review report downloaded successfully', 'polite');
    } catch (err: any) {
      console.error('Failed to download report:', err);
      setError(getApiErrorMessage(err, 'Failed to download review report'));
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
      setError(getApiErrorMessage(err, 'Failed to complete review'));
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

  // Show message if no findings need review
  if (findings.length === 0 && !loading) {
    console.log('HILReview: Rendering no findings message');
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="info">
          No findings require human review for this run.
          {reviewStatus && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Total findings: {reviewStatus.total_findings}, 
              Reviewed: {reviewStatus.reviewed_count}, 
              Pending: {reviewStatus.pending_count}
            </Typography>
          )}
        </Alert>
        <Box sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}
            aria-label="Navigate back to results page"
          >
            Back to Results
          </Button>
        </Box>
      </Container>
    );
  }
  
  console.log('HILReview: Rendering main review UI. Findings count:', findings.length);
  
  if (!hasReviewPermission) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">
          You do not have permission to review findings. Contact an administrator for access.
        </Alert>
        <Box sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(`/applications/${applicationId}/runs/${runId}`)}
            aria-label="Navigate back to results page"
          >
            Back to Results
          </Button>
        </Box>
      </Container>
    );
  }

  const currentFinding = findings[currentIndex];
  const progress = reviewStatus && reviewStatus.total_findings > 0
    ? (reviewStatus.reviewed_count / reviewStatus.total_findings) * 100
    : 0;

  // Safety check - ensure currentFinding exists before rendering
  if (!currentFinding) {
    console.warn('HILReview: currentFinding is undefined at index', currentIndex, 'findings length:', findings.length);
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="warning">
          Unable to load finding data. Please try refreshing the page.
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

  return (
    <Box sx={{ display: 'flex', ml: { sm: 0 }, minHeight: 'calc(100vh - 64px)' }}>
      {/* Sidebar Navigation - positioned after the Layout's drawer */}
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          display: { xs: 'none', md: 'block' }, // Hide on small screens to avoid overlap
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            position: 'fixed',
            left: { sm: LAYOUT_DRAWER_WIDTH }, // Position after Layout drawer
            top: 64, // Below AppBar
            height: 'calc(100vh - 64px)',
            borderRight: '1px solid rgba(0, 0, 0, 0.12)',
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
            aria-label="Navigate back to results page"
          >
            Back to Results
          </Button>
          <Button
            fullWidth
            variant="contained"
            color="primary"
            onClick={handleDownloadReport}
            sx={{ mb: 1 }}
            aria-label="Download review report as PDF"
          >
            Download Report
          </Button>
          <Button
            fullWidth
            variant="contained"
            color="success"
            startIcon={<Save />}
            onClick={() => setShowCompleteDialog(true)}
            disabled={reviewStatus?.pending_count !== 0 || !hasReviewPermission}
            aria-label={reviewStatus?.pending_count !== 0 ? `Complete review disabled - ${reviewStatus?.pending_count} findings still pending` : 'Complete review'}
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

      {/* Main Content - account for the fixed sidebar drawer */}
      <Box 
        component="main" 
        sx={{ 
          flexGrow: 1, 
          p: 3,
          ml: { md: `${DRAWER_WIDTH}px` }, // Offset for the fixed sidebar on medium+ screens
          width: { xs: '100%', md: `calc(100% - ${DRAWER_WIDTH}px)` },
        }} 
        id="main-content"
      >
        <Container maxWidth="md">
          {/* LLM Call Tracker */}
          <LLMCallTracker
            calls={llmCalls}
            totalTokens={totalTokens}
            totalCalls={totalCalls}
          />
          
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
                  aria-label="Previous finding"
                >
                  <NavigateBefore />
                </IconButton>
                <IconButton
                  onClick={() => setCurrentIndex(Math.min(findings.length - 1, currentIndex + 1))}
                  disabled={currentIndex === findings.length - 1}
                  aria-label="Next finding"
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
              disabled={submitting || !hasReviewPermission}
              aria-label="Add comment for review decision"
            />

            <Stack direction="row" spacing={2} justifyContent="center">
              <Button
                variant="contained"
                color="success"
                size="large"
                startIcon={<CheckCircle />}
                onClick={() => handleDecision('accept')}
                disabled={submitting || !hasReviewPermission}
                sx={{ minWidth: 140 }}
                aria-label="Accept this finding"
              >
                Accept
              </Button>
              <Button
                variant="contained"
                color="error"
                size="large"
                startIcon={<Cancel />}
                onClick={() => handleDecision('reject')}
                disabled={submitting || !hasReviewPermission}
                sx={{ minWidth: 140 }}
                aria-label="Reject this finding"
              >
                Reject
              </Button>
              <Button
                variant="contained"
                color="warning"
                size="large"
                startIcon={<HelpOutline />}
                onClick={() => handleDecision('need_info')}
                disabled={submitting || !hasReviewPermission}
                sx={{ minWidth: 140 }}
                aria-label="Mark this finding as needing more information"
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
