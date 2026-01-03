import { Box, Typography, Stack, Paper, Chip, Alert, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { 
  Error, 
  Warning, 
  Info, 
  CheckCircle, 
  ExpandMore,
  Description,
  Visibility,
  Assignment,
  Payment,
  Verified,
  CompareArrows,
  History,
  Place,
  Nature,
  Architecture
} from '@mui/icons-material';

interface ValidationFinding {
  rule_id: string;
  title: string;
  status: string;
  severity: string;
  message: string;
  evidence?: any[];
  evidence_details?: any[];
  candidate_documents?: any[];
  document_name?: string;
  rule_category?: string;
}

interface ValidationFindingsDisplayProps {
  findings: ValidationFinding[];
  onViewDocument?: (documentId: number, evidenceDetails?: any) => void;
}

// Category-based organization with user-friendly labels
const CATEGORY_CONFIG: Record<string, {
  label: string;
  icon: JSX.Element;
  description: string;
  priority: number;
  color: 'error' | 'warning' | 'info' | 'success';
}> = {
  PRIOR_APPROVAL: {
    label: 'Prior Approval',
    icon: <CheckCircle />,
    description: 'Special requirements for prior approval applications',
    priority: 1,
    color: 'warning',
  },
  DOCUMENT_REQUIRED: {
    label: 'Required Documents',
    icon: <Description />,
    description: 'Documents that must be submitted with the application',
    priority: 2,
    color: 'error',
  },
  FIELD_REQUIRED: {
    label: 'Required Information',
    icon: <Assignment />,
    description: 'Essential fields that must be completed in the application form',
    priority: 3,
    color: 'error',
  },
  FEE_VALIDATION: {
    label: 'Fee Validation',
    icon: <Payment />,
    description: 'Application fee and payment verification',
    priority: 4,
    color: 'error',
  },
  OWNERSHIP_VALIDATION: {
    label: 'Ownership Certificate',
    icon: <Verified />,
    description: 'Property ownership certification requirements',
    priority: 5,
    color: 'error',
  },
  CONSTRAINT_VALIDATION: {
    label: 'Planning Constraints',
    icon: <Warning />,
    description: 'Heritage, conservation area, TPO, and flood zone requirements',
    priority: 6,
    color: 'warning',
  },
  BNG_VALIDATION: {
    label: 'Biodiversity Net Gain',
    icon: <Nature />,
    description: '10% biodiversity improvement requirements',
    priority: 7,
    color: 'warning',
  },
  CONSISTENCY: {
    label: 'Data Consistency',
    icon: <CompareArrows />,
    description: 'Information must match across all documents',
    priority: 8,
    color: 'warning',
  },
  PLAN_QUALITY: {
    label: 'Plan Quality Standards',
    icon: <Architecture />,
    description: 'Technical standards for drawings and plans',
    priority: 9,
    color: 'info',
  },
  MODIFICATION: {
    label: 'Modification Tracking',
    icon: <History />,
    description: 'Requirements for amended or resubmitted applications',
    priority: 10,
    color: 'info',
  },
  SPATIAL: {
    label: 'Location Validation',
    icon: <Place />,
    description: 'Geographic and boundary requirements',
    priority: 11,
    color: 'info',
  },
};

// Better status labels with enhanced "Needs Review" guidance
const STATUS_LABELS: Record<string, { label: string; description: string }> = {
  missing: {
    label: 'Missing Information',
    description: 'Required information was not found in the documents',
  },
  incomplete: {
    label: 'Incomplete',
    description: 'Information is present but incomplete or unclear',
  },
  needs_review: {
    label: 'Needs Manual Verification',
    description: 'This item requires manual verification by a planning officer. The automated system has identified relevant information but cannot automatically determine compliance. Please review the evidence below and make a decision.',
  },
  not_found: {
    label: 'Not Found',
    description: 'Expected information could not be located',
  },
  found: {
    label: 'Found',
    description: 'Information has been located and verified',
  },
  pass: {
    label: 'Passed',
    description: 'This check has passed successfully',
  },
  fail: {
    label: 'Failed',
    description: 'This check has failed and requires attention',
  },
};

// Get color based on status and severity
const getStatusColor = (status: string, severity: string): 'error' | 'warning' | 'info' | 'success' => {
  if (status === 'pass') return 'success';
  if (status === 'needs_review') return 'warning';
  if (status === 'fail' || status === 'missing') {
    return severity === 'error' ? 'error' : 'warning';
  }
  return 'info';
};

export default function ValidationFindingsDisplay({ findings, onViewDocument }: ValidationFindingsDisplayProps) {
  // Group by category
  const groupedByCategory = findings.reduce((acc, finding) => {
    const category = finding.rule_category || 'FIELD_REQUIRED';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(finding);
    return acc;
  }, {} as Record<string, ValidationFinding[]>);

  // Remove duplicates within each category
  const deduplicateFindings = (findings: ValidationFinding[]): ValidationFinding[] => {
    const seen = new Set<string>();
    return findings.filter(finding => {
      const key = `${finding.rule_id}:${finding.message}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  // Get all categories sorted by priority
  const allCategories = Object.keys(CATEGORY_CONFIG).sort((a, b) => 
    CATEGORY_CONFIG[a].priority - CATEGORY_CONFIG[b].priority
  );

  // Check if all findings are passed
  const allPassed = findings.length > 0 && findings.every(f => f.status === 'pass');

  if (findings.length === 0) {
    return (
      <Alert severity="success" icon={<CheckCircle />} sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>✅ All Checks Passed</Typography>
        <Typography variant="body2">
          No issues found - all validation checks have passed successfully!
        </Typography>
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      {allCategories.map((categoryKey) => {
        const config = CATEGORY_CONFIG[categoryKey];
        const categoryFindings = deduplicateFindings(groupedByCategory[categoryKey] || []);
        
        // Count pass/fail
        const passedCount = categoryFindings.filter(f => f.status === 'pass').length;
        const issueCount = categoryFindings.length - passedCount;
        
        // If no findings in this category, show as "No issues"
        if (categoryFindings.length === 0) {
          return (
            <Paper key={categoryKey} elevation={1} sx={{ p: 2.5, bgcolor: 'success.lighter', borderLeft: '4px solid', borderLeftColor: 'success.main' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <CheckCircle color="success" />
                <Typography variant="body1" fontWeight={600} color="success.main">
                  ✓ {config.label}: No issues
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ ml: 4.5, mt: 0.5 }}>
                {config.description}
              </Typography>
            </Paper>
          );
        }

        return (
          <Paper key={categoryKey} elevation={2} sx={{ overflow: 'hidden' }}>
            <Accordion defaultExpanded={issueCount > 0} sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
              <AccordionSummary 
                expandIcon={<ExpandMore />}
                sx={{ 
                  bgcolor: issueCount > 0 ? `${config.color}.lighter` : 'grey.50',
                  borderLeft: '4px solid',
                  borderLeftColor: issueCount > 0 ? `${config.color}.main` : 'success.main',
                  '&:hover': { bgcolor: issueCount > 0 ? `${config.color}.light` : 'grey.100' }
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
                  {config.icon}
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {config.label}
                  </Typography>
                  {issueCount > 0 ? (
                    <Chip 
                      label={`${issueCount} ${issueCount === 1 ? 'issue' : 'issues'}`}
                      color={config.color}
                      size="small"
                    />
                  ) : (
                    <Chip 
                      label="All passed"
                      color="success"
                      size="small"
                      icon={<CheckCircle />}
                    />
                  )}
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                    {categoryFindings.length} {categoryFindings.length === 1 ? 'check' : 'checks'}
                  </Typography>
                </Box>
              </AccordionSummary>
              
              <AccordionDetails sx={{ p: 3, bgcolor: 'background.default' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3, fontStyle: 'italic' }}>
                  {config.description}
                </Typography>

                <Stack spacing={2}>
                  {categoryFindings.map((finding, index) => {
                    const statusInfo = STATUS_LABELS[finding.status] || { 
                      label: finding.status, 
                      description: '' 
                    };
                    const statusColor = getStatusColor(finding.status, finding.severity);

                    return (
                      <Box
                        key={`${finding.rule_id}-${index}`}
                        sx={{
                          p: 2.5,
                          border: '1px solid',
                          borderColor: finding.status === 'pass' ? 'success.main' : `${statusColor}.main`,
                          borderRadius: 1,
                          borderLeft: '4px solid',
                          borderLeftColor: finding.status === 'pass' ? 'success.main' : `${statusColor}.main`,
                          backgroundColor: finding.status === 'pass' ? 'success.lighter' : `${statusColor}.lighter`,
                        }}
                      >
                        {/* Header with status and rule info */}
                        <Box sx={{ display: 'flex', gap: 1, mb: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
                          <Chip 
                            label={statusInfo.label}
                            color={statusColor}
                            size="small"
                            icon={finding.status === 'pass' ? <CheckCircle /> : finding.status === 'needs_review' ? <Info /> : <Warning />}
                          />
                          <Chip 
                            label={finding.rule_id}
                            size="small" 
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                          {finding.document_name && (
                            <Chip 
                              label={finding.document_name} 
                              size="small" 
                              icon={<Description />}
                              variant="outlined"
                            />
                          )}
                        </Box>

                        {/* Rule Title - Primary heading in natural language */}
                        <Typography variant="h6" gutterBottom sx={{ fontSize: '1.1rem', fontWeight: 600, color: 'text.primary' }}>
                          {finding.title || statusInfo.label}
                        </Typography>

                        {/* Main Message */}
                        <Typography variant="body1" sx={{ mb: 1.5 }}>
                          {finding.message}
                        </Typography>

                        {/* Status Description - Enhanced for needs_review */}
                        {statusInfo.description && finding.status === 'needs_review' && (
                          <Alert severity="warning" icon={<Info />} sx={{ mb: 2 }}>
                            <Typography variant="body2">
                              {statusInfo.description}
                            </Typography>
                          </Alert>
                        )}

                        {/* Evidence Details */}
                        {finding.evidence_details && finding.evidence_details.length > 0 && (
                          <Accordion sx={{ mt: 2, backgroundColor: 'rgba(255,255,255,0.7)' }}>
                            <AccordionSummary expandIcon={<ExpandMore />}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Visibility fontSize="small" />
                                <Typography variant="body2" fontWeight="medium">
                                  View Evidence ({finding.evidence_details.length} {finding.evidence_details.length === 1 ? 'source' : 'sources'})
                                </Typography>
                              </Box>
                            </AccordionSummary>
                            <AccordionDetails>
                              <Stack spacing={1.5}>
                                {finding.evidence_details.map((evidence: any, idx: number) => (
                                  <Box
                                    key={idx}
                                    sx={{
                                      p: 2,
                                      backgroundColor: 'background.paper',
                                      borderRadius: 1,
                                      border: '1px solid',
                                      borderColor: 'divider',
                                    }}
                                  >
                                    {evidence.document_name && (
                                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                        <Description fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
                                        {evidence.document_name} - Page {evidence.page}
                                      </Typography>
                                    )}
                                    <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                                      "{evidence.snippet}"
                                    </Typography>
                                  </Box>
                                ))}
                              </Stack>
                            </AccordionDetails>
                          </Accordion>
                        )}

                        {/* Candidate Documents - NO CONFIDENCE PERCENTAGES */}
                        {finding.candidate_documents && finding.candidate_documents.length > 0 && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                              Suggested documents to review:
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              {finding.candidate_documents.map((doc: any, idx: number) => (
                                <Chip
                                  key={idx}
                                  label={doc.document_name}
                                  size="small"
                                  icon={<Description />}
                                  onClick={() => onViewDocument && onViewDocument(doc.document_id)}
                                  sx={{ cursor: 'pointer' }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}
                      </Box>
                    );
                  })}
                </Stack>
              </AccordionDetails>
            </Accordion>
          </Paper>
        );
      })}
    </Stack>
  );
}
