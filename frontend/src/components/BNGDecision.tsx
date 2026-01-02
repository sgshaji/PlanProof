import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Alert,
  Chip,
  Stack,
  CircularProgress,
} from '@mui/material';
import { CheckCircle, Nature } from '@mui/icons-material';

interface BNGDecisionProps {
  runId: number;
  currentBNGStatus?: {
    applicable: boolean | null;
    exemptionReason?: string;
  };
  onDecisionSubmitted: () => void;
}

const BNGDecision: React.FC<BNGDecisionProps> = ({
  runId,
  currentBNGStatus,
  onDecisionSubmitted,
}) => {
  const [bngApplicable, setBngApplicable] = useState<string>(
    currentBNGStatus?.applicable === null
      ? ''
      : currentBNGStatus?.applicable
      ? 'yes'
      : 'no'
  );
  const [exemptionReason, setExemptionReason] = useState(
    currentBNGStatus?.exemptionReason || ''
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!bngApplicable) {
      setError('Please select whether BNG applies to this application');
      return;
    }

    if (bngApplicable === 'no' && !exemptionReason.trim()) {
      setError('Please provide a reason why BNG does not apply');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const { api } = await import('../api/client');
      await api.submitBNGDecision(
        runId,
        bngApplicable === 'yes',
        bngApplicable === 'no' ? exemptionReason : undefined
      );
      onDecisionSubmitted();
    } catch (err: any) {
      const { getApiErrorMessage } = await import('../api/errorUtils');
      setError(getApiErrorMessage(err, 'Failed to submit BNG decision'));
    } finally {
      setSubmitting(false);
    }
  };

  // If already decided, show status
  if (currentBNGStatus && currentBNGStatus.applicable !== null) {
    return (
      <Paper elevation={2} sx={{ p: 3, mb: 3, backgroundColor: 'success.lighter' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Nature color="success" />
          <Typography variant="h6">Biodiversity Net Gain (BNG) - Recorded</Typography>
          <Chip
            icon={<CheckCircle />}
            label={currentBNGStatus.applicable ? 'Applicable' : 'Not Applicable'}
            color={currentBNGStatus.applicable ? 'success' : 'warning'}
            size="small"
          />
        </Box>
        
        {!currentBNGStatus.applicable && currentBNGStatus.exemptionReason && (
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Exemption Reason:
            </Typography>
            <Typography variant="body1">
              {currentBNGStatus.exemptionReason}
            </Typography>
          </Box>
        )}
        
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          To change this decision, you would need to rerun validation.
        </Typography>
      </Paper>
    );
  }

  // Decision form
  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3, backgroundColor: 'info.lighter' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Nature color="info" />
        <Typography variant="h6">Biodiversity Net Gain (BNG) Decision Required</Typography>
      </Box>

      <Typography variant="body1" gutterBottom sx={{ mb: 3 }}>
        Please indicate whether Biodiversity Net Gain requirements apply to this planning application.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <RadioGroup
        value={bngApplicable}
        onChange={(e) => setBngApplicable(e.target.value)}
        sx={{ mb: 3 }}
      >
        <FormControlLabel
          value="yes"
          control={<Radio />}
          label={
            <Box>
              <Typography variant="body1">Yes, BNG applies to this application</Typography>
              <Typography variant="caption" color="text.secondary">
                This application must demonstrate at least 10% biodiversity net gain
              </Typography>
            </Box>
          }
        />
        <FormControlLabel
          value="no"
          control={<Radio />}
          label={
            <Box>
              <Typography variant="body1">No, BNG does not apply</Typography>
              <Typography variant="caption" color="text.secondary">
                This application is exempt from BNG requirements
              </Typography>
            </Box>
          }
        />
      </RadioGroup>

      {bngApplicable === 'no' && (
        <TextField
          fullWidth
          multiline
          rows={3}
          label="Exemption Reason *"
          placeholder="E.g., Householder application, minor development under threshold, self-build custom build..."
          value={exemptionReason}
          onChange={(e) => setExemptionReason(e.target.value)}
          sx={{ mb: 3 }}
          helperText="Please specify why BNG does not apply to this application"
        />
      )}

      <Stack direction="row" spacing={2}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSubmit}
          disabled={submitting || !bngApplicable}
          startIcon={submitting ? <CircularProgress size={20} /> : <CheckCircle />}
        >
          {submitting ? 'Submitting...' : 'Submit BNG Decision'}
        </Button>
      </Stack>

      <Box sx={{ mt: 3, p: 2, backgroundColor: 'grey.100', borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          <strong>Note:</strong> The Town and Country Planning (Biodiversity Gain) (England) Regulations 2024
          require most planning applications to demonstrate at least 10% biodiversity net gain. Common exemptions
          include householder applications, some permitted development rights, and self-build/custom-build developments.
        </Typography>
      </Box>
    </Paper>
  );
};

export default BNGDecision;
