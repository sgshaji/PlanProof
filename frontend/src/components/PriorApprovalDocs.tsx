import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Button,
  Alert,
  Chip,
  Stack,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Description,
  CheckCircle,
  Error,
  Save,
} from '@mui/icons-material';
import { api } from '../api/client';

interface PriorApprovalDocsProps {
  runId: number;
  submissionId: number;
  onUpdate?: () => void;
}

const REQUIRED_DOCUMENTS = [
  {
    id: 'application_form',
    label: 'Application Form',
    description: 'Completed Prior Approval application form',
  },
  {
    id: 'location_plan',
    label: 'Location Plan',
    description: 'Site location plan at appropriate scale (1:1250 or 1:2500)',
  },
  {
    id: 'site_plan',
    label: 'Site Plan',
    description: 'Detailed site plan showing proposed development',
  },
  {
    id: 'elevations',
    label: 'Elevations',
    description: 'Proposed and existing elevations where applicable',
  },
  {
    id: 'design_statement',
    label: 'Design and Access Statement',
    description: 'Design and Access Statement if required',
  },
];

const PriorApprovalDocs: React.FC<PriorApprovalDocsProps> = ({ runId, submissionId, onUpdate }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [presentDocs, setPresentDocs] = useState<Set<string>>(new Set());
  const [customRequirements, setCustomRequirements] = useState<string[]>([]);

  useEffect(() => {
    loadDocumentRequirements();
  }, [runId, submissionId]);

  const loadDocumentRequirements = async () => {
    setLoading(true);
    setError(null);

    try {
      // TODO: Implement API endpoint to get document requirements
      // For now, show placeholder
      setError('Prior Approval document requirements endpoint not yet implemented');
      setLoading(false);
      
      // Mock data for demonstration
      // const response = await api.getPriorApprovalDocs(runId, submissionId);
      // setPresentDocs(new Set(response.present_documents));
      // setCustomRequirements(response.custom_requirements || []);
      // setLoading(false);
    } catch (err: any) {
      console.error('Failed to load document requirements:', err);
      setError(err.message || 'Failed to load document requirements');
      setLoading(false);
    }
  };

  const handleSaveRequirements = async () => {
    setSaving(true);
    setError(null);

    try {
      // TODO: Implement API endpoint to save document requirements
      // await api.updatePriorApprovalDocs(runId, submissionId, {
      //   required_documents: REQUIRED_DOCUMENTS.map(d => d.id),
      //   present_documents: Array.from(presentDocs),
      //   custom_requirements: customRequirements,
      // });
      
      if (onUpdate) {
        onUpdate();
      }
      
      setSaving(false);
    } catch (err: any) {
      console.error('Failed to save requirements:', err);
      setError(err.message || 'Failed to save requirements');
      setSaving(false);
    }
  };

  const handleToggleDocument = (docId: string) => {
    setPresentDocs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  const getMissingCount = () => {
    return REQUIRED_DOCUMENTS.filter((doc) => !presentDocs.has(doc.id)).length;
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <CircularProgress size={24} />
            <Typography>Loading Prior Approval document requirements...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="info">
            <Typography variant="body2" gutterBottom>
              {error}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              To enable Prior Approval document management, implement GET/POST endpoints for
              /api/v1/runs/{'{'}runId{'}'}/prior-approval-docs to retrieve and update document requirements.
            </Typography>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const missingCount = getMissingCount();

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Description color="primary" />
            <Typography variant="h6">Prior Approval Document Requirements</Typography>
          </Box>
          {missingCount === 0 ? (
            <Chip
              icon={<CheckCircle />}
              label="All documents present"
              color="success"
              size="small"
            />
          ) : (
            <Chip
              icon={<Error />}
              label={`${missingCount} missing`}
              color="error"
              size="small"
            />
          )}
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            Prior Approval applications require a specific set of documents. Check the boxes below to
            confirm which documents are present in this submission.
          </Typography>
        </Alert>

        <FormGroup>
          <Stack spacing={1.5}>
            {REQUIRED_DOCUMENTS.map((doc) => {
              const isPresent = presentDocs.has(doc.id);
              return (
                <Box
                  key={doc.id}
                  sx={{
                    p: 2,
                    border: '1px solid',
                    borderColor: isPresent ? 'success.main' : 'grey.300',
                    borderRadius: 1,
                    backgroundColor: isPresent ? 'success.50' : 'transparent',
                    transition: 'all 0.2s',
                  }}
                >
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={isPresent}
                        onChange={() => handleToggleDocument(doc.id)}
                        color="success"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body1" fontWeight={600}>
                          {doc.label}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {doc.description}
                        </Typography>
                      </Box>
                    }
                  />
                </Box>
              );
            })}
          </Stack>
        </FormGroup>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            {REQUIRED_DOCUMENTS.length} total requirements • {presentDocs.size} present • {missingCount} missing
          </Typography>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <Save />}
            onClick={handleSaveRequirements}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Requirements'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default PriorApprovalDocs;
