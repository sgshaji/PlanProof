import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  alpha,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import AssignmentIcon from '@mui/icons-material/Assignment';
import DescriptionIcon from '@mui/icons-material/Description';

interface EvidenceDetail {
  page?: number;
  snippet?: string;
  document_name?: string;
  confidence?: number;
}

interface CandidateDocument {
  document_name: string;
  confidence?: number;
  reason?: string;
  scanned?: boolean;
}

interface ValidationFinding {
  id: number;
  rule_id: string;
  title: string;
  status: string;
  severity: string;
  message: string;
  formatted_message?: string;
  action_guidance?: string;
  evidence_details?: EvidenceDetail[];
  candidate_documents?: CandidateDocument[];
  document_name?: string;
}

interface ValidationFindingCardProps {
  finding: ValidationFinding;
  showEvidence?: boolean;
}

const ValidationFindingCard: React.FC<ValidationFindingCardProps> = ({
  finding,
  showEvidence = true,
}) => {
  const [expandedEvidence, setExpandedEvidence] = useState(false);
  const [expandedDocs, setExpandedDocs] = useState(false);

  const getSeverityIcon = () => {
    switch (finding.severity) {
      case 'error':
      case 'critical':
      case 'blocker':
        return <ErrorIcon />;
      case 'warning':
        return <WarningIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getSeverityColor = () => {
    switch (finding.severity) {
      case 'error':
      case 'critical':
      case 'blocker':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };

  const getBorderColor = () => {
    switch (finding.severity) {
      case 'error':
      case 'critical':
      case 'blocker':
        return alpha('#d32f2f', 0.3);
      case 'warning':
        return alpha('#ed6c02', 0.3);
      default:
        return alpha('#0288d1', 0.3);
    }
  };

  const displayMessage = finding.formatted_message || finding.message;
  const hasEvidence = finding.evidence_details && finding.evidence_details.length > 0;
  const hasCandidateDocs = finding.candidate_documents && finding.candidate_documents.length > 0;

  return (
    <Card
      variant="outlined"
      sx={{
        borderLeft: `4px solid ${getBorderColor()}`,
        borderColor: getBorderColor(),
        mb: 2,
        transition: 'all 0.2s',
        '&:hover': {
          boxShadow: 2,
        },
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
          <Box sx={{ color: `${getSeverityColor()}.main`, mt: 0.5 }}>
            {getSeverityIcon()}
          </Box>

          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1, flexWrap: 'wrap' }}>
              <Chip
                label={finding.rule_id}
                size="small"
                color={getSeverityColor()}
                variant="outlined"
                sx={{ fontWeight: 600 }}
              />

              <Chip
                label={finding.severity.toUpperCase()}
                size="small"
                color={getSeverityColor()}
              />

              {finding.document_name && (
                <Chip
                  icon={<DescriptionIcon fontSize="small" />}
                  label={finding.document_name}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>

            <Typography variant="body1" sx={{ mb: 1, fontWeight: 500 }}>
              {displayMessage}
            </Typography>

            {finding.action_guidance && (
              <Alert severity={getSeverityColor()} icon={<AssignmentIcon />} sx={{ mb: 2 }}>
                <Typography variant="body2">
                  <strong>Action Required:</strong> {finding.action_guidance}
                </Typography>
              </Alert>
            )}

            {showEvidence && hasEvidence && (
              <Accordion
                expanded={expandedEvidence}
                onChange={() => setExpandedEvidence(!expandedEvidence)}
                elevation={0}
                sx={{ mt: 2 }}
              >
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  sx={{
                    bgcolor: alpha('#1976d2', 0.05),
                    '&:hover': { bgcolor: alpha('#1976d2', 0.1) },
                  }}
                >
                  <Typography variant="body2" fontWeight={600}>
                    Evidence ({finding.evidence_details?.length || 0})
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {finding.evidence_details?.map((evidence, index) => (
                      <Card
                        key={index}
                        variant="outlined"
                        sx={{ bgcolor: alpha('#f5f5f5', 0.5) }}
                      >
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                            {evidence.document_name && (
                              <Chip
                                label={evidence.document_name}
                                size="small"
                                variant="outlined"
                              />
                            )}
                            {evidence.page && (
                              <Chip label={`Page ${evidence.page}`} size="small" />
                            )}
                            {evidence.confidence !== undefined && (
                              <Chip
                                label={`${(evidence.confidence * 100).toFixed(0)}% confidence`}
                                size="small"
                                color={evidence.confidence > 0.7 ? 'success' : 'default'}
                              />
                            )}
                          </Box>

                          {evidence.snippet && (
                            <Typography
                              variant="body2"
                              sx={{
                                fontFamily: 'monospace',
                                bgcolor: 'white',
                                p: 1,
                                borderRadius: 1,
                                fontSize: '0.85rem',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                              }}
                            >
                              {evidence.snippet}
                            </Typography>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}

            {showEvidence && hasCandidateDocs && (
              <Accordion
                expanded={expandedDocs}
                onChange={() => setExpandedDocs(!expandedDocs)}
                elevation={0}
                sx={{ mt: 1 }}
              >
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  sx={{
                    bgcolor: alpha('#1976d2', 0.05),
                    '&:hover': { bgcolor: alpha('#1976d2', 0.1) },
                  }}
                >
                  <Typography variant="body2" fontWeight={600}>
                    Documents to Check ({finding.candidate_documents?.length || 0})
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {finding.candidate_documents?.map((doc, index) => (
                      <Box
                        key={index}
                        sx={{
                          p: 1.5,
                          bgcolor: alpha('#f5f5f5', 0.5),
                          borderRadius: 1,
                          border: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                          {doc.document_name}
                        </Typography>

                        {doc.reason && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            {doc.reason}
                          </Typography>
                        )}

                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          {doc.confidence !== undefined && (
                            <Chip
                              label={`${(doc.confidence * 100).toFixed(0)}% relevance`}
                              size="small"
                              color={doc.confidence > 0.7 ? 'success' : 'default'}
                            />
                          )}
                          {doc.scanned && (
                            <Chip label="Scanned" size="small" color="info" />
                          )}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ValidationFindingCard;
