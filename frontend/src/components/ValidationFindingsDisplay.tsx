import { useState } from 'react';
import { Box, Typography, Stack, Paper, Chip, Alert, Accordion, AccordionSummary, AccordionDetails, Button } from '@mui/material';
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
import { useNavigate } from 'react-router-dom';

interface ValidationFinding {
  rule_id: string;
  title: string;
  description?: string;
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
  runId?: number;
  applicationId?: number;
}

// Evidence Accordion Component with pagination
function EvidenceAccordion({ 
  evidence, 
  defaultExpanded = false, 
  prominent = false 
}: { 
  evidence: any[]; 
  defaultExpanded?: boolean; 
  prominent?: boolean;
}) {
  const [showAll, setShowAll] = useState(false);
  const INITIAL_DISPLAY_COUNT = 10;
  
  const displayedEvidence = showAll ? evidence : evidence.slice(0, INITIAL_DISPLAY_COUNT);
  const hasMore = evidence.length > INITIAL_DISPLAY_COUNT;
  
  return (
    <Accordion 
      defaultExpanded={defaultExpanded}
      sx={{ 
        mt: 2, 
        backgroundColor: prominent ? 'rgba(25, 118, 210, 0.08)' : 'rgba(255,255,255,0.7)',
        border: prominent ? '2px solid' : '1px solid',
        borderColor: prominent ? 'primary.main' : 'divider',
      }}
    >
      <AccordionSummary 
        expandIcon={<ExpandMore />}
        sx={{
          backgroundColor: prominent ? 'rgba(25, 118, 210, 0.04)' : 'transparent',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Visibility fontSize="small" color={prominent ? 'primary' : 'action'} />
          <Typography 
            variant="body2" 
            fontWeight={prominent ? 600 : 500}
            color={prominent ? 'primary.main' : 'text.primary'}
          >
            Evidence Found ({evidence.length} {evidence.length === 1 ? 'source' : 'sources'})
          </Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.5}>
          {displayedEvidence.map((item: any, idx: number) => (
            <Paper
              key={idx}
              elevation={prominent ? 2 : 1}
              sx={{
                p: 2,
                backgroundColor: 'background.paper',
                borderLeft: prominent ? '3px solid' : '1px solid',
                borderLeftColor: prominent ? 'primary.main' : 'divider',
              }}
            >
              {item.document_name && (
                <Typography 
                  variant="caption" 
                  color={prominent ? 'primary' : 'text.secondary'} 
                  sx={{ display: 'block', mb: 0.5, fontWeight: prominent ? 600 : 400 }}
                >
                  <Description fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
                  {item.document_name} - Page {item.page}
                </Typography>
              )}
              <Typography 
                variant="body2" 
                sx={{ 
                  fontStyle: 'italic', 
                  color: prominent ? 'text.primary' : 'text.secondary',
                  lineHeight: 1.6 
                }}
              >
                "{item.snippet}"
              </Typography>
            </Paper>
          ))}
          
          {/* Show More / Show Less Button */}
          {hasMore && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <Button
                variant="outlined"
                size="small"
                onClick={() => setShowAll(!showAll)}
                sx={{ textTransform: 'none' }}
              >
                {showAll 
                  ? `Show Less` 
                  : `Show ${evidence.length - INITIAL_DISPLAY_COUNT} More Evidence Items`
                }
              </Button>
            </Box>
          )}
          
          {/* Summary when showing all */}
          {showAll && hasMore && (
            <Typography 
              variant="caption" 
              color="text.secondary" 
              sx={{ display: 'block', textAlign: 'center', mt: 1 }}
            >
              Showing all {evidence.length} evidence items
            </Typography>
          )}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
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

// Rule descriptions - plain language explanations of what each rule checks
const RULE_DESCRIPTIONS: Record<string, string> = {
  // Document requirements
  'DOC-001': 'All planning applications must include accurate location plans showing the site boundary.',
  'DOC-002': 'Block plans must show the proposed development in context with neighboring properties.',
  'DOC-003': 'Elevation drawings are required to show all external faces of the building.',
  'DOC-004': 'Floor plans must show the layout and room dimensions for all floors.',
  'DOC-005': 'Design and access statements explain how the proposal fits the site and area.',

  // Field requirements
  'FIELD-001': 'The application reference number must be provided for tracking purposes.',
  'FIELD-002': 'The site address must be complete and accurate for location identification.',
  'FIELD-003': 'Applicant details are required for correspondence and legal purposes.',
  'FIELD-004': 'The proposal description must clearly explain what is being applied for.',
  'FIELD-005': 'Development type classification helps determine processing requirements.',

  // Prior Approval
  'PA-01': 'Prior approval applications for permitted development must include specific evidence as required by the GPDO.',
  'PA-02': 'Transport and highways impact must be assessed for prior approval applications.',
  'PA-03': 'Contamination risks must be evaluated for prior approval applications.',
  'PA-04': 'Flooding risks must be considered for prior approval applications.',
  'PA-05': 'Noise impacts on residential amenity must be assessed.',

  // Fees
  'FEE-001': 'The correct application fee must be calculated and paid based on the development type and scale.',
  'FEE-002': 'Fee exemptions must be properly documented and justified.',

  // Ownership
  'OWN-001': 'A valid ownership certificate (A, B, C, or D) must be completed confirming the applicant\'s interest in the land.',
  'OWN-002': 'Certificate B requires notice to be served on other landowners with details provided.',
  'OWN-003': 'Agricultural land notice requirements apply when part of the site has been agricultural land in the last 10 years.',

  // Constraints
  'CON-001': 'Heritage asset impacts must be properly assessed if the site affects listed buildings or conservation areas.',
  'CON-002': 'Tree preservation orders require specific justification and mitigation for tree works.',
  'CON-003': 'Flood risk assessments are required for sites in flood zones 2 or 3.',
  'CON-004': 'Conservation area consent may be required for demolition or certain works.',

  // BNG
  'BNG-001': 'Biodiversity Net Gain of at least 10% must be demonstrated for major developments.',
  'BNG-002': 'A biodiversity gain plan must show how the 10% gain will be achieved and maintained.',
  'BNG-003': 'Habitat condition assessments must use the statutory biodiversity metric.',

  // Plan quality
  'PLAN-001': 'Plans must include a north arrow for correct orientation.',
  'PLAN-002': 'All plans must be drawn to a stated metric scale.',
  'PLAN-003': 'Plans must show accurate dimensions and measurements.',
  'PLAN-004': 'Site boundary must be clearly marked with a red line on all plans.',
  'PLAN-005': 'Plans must be clear, legible, and of sufficient quality to assess the proposal.',
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

export default function ValidationFindingsDisplay({ findings, onViewDocument, runId, applicationId }: ValidationFindingsDisplayProps) {
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
  const needsReviewCount = findings.filter(f => f.status === 'needs_review').length;
  const navigate = useNavigate();

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
      {/* Needs Review Summary Banner */}
      {needsReviewCount > 0 && runId && applicationId && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                ⚠️ {needsReviewCount} {needsReviewCount === 1 ? 'Item Needs' : 'Items Need'} Manual Review
              </Typography>
              <Typography variant="body2" color="text.secondary">
                These items require verification by a planning officer. The AI found relevant information but cannot automatically determine compliance.
              </Typography>
            </Box>
            <Button
              variant="contained"
              color="warning"
              onClick={() => navigate(`/applications/${applicationId}/runs/${runId}/review`)}
              sx={{ ml: 2, whiteSpace: 'nowrap' }}
            >
              Start Review
            </Button>
          </Box>
        </Alert>
      )}

      {allCategories.map((categoryKey) => {
        const config = CATEGORY_CONFIG[categoryKey];
        const categoryFindings = deduplicateFindings(groupedByCategory[categoryKey] || []);

        // Count pass/fail
        const passedCount = categoryFindings.filter(f => f.status === 'pass').length;
        const issueCount = categoryFindings.length - passedCount;

        // Skip categories with no findings at all - don't show empty categories
        if (categoryFindings.length === 0) {
          return null;
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
                    const ruleDescription = RULE_DESCRIPTIONS[finding.rule_id];
                    const isNeedsReview = finding.status === 'needs_review';
                    const hasEvidence = finding.evidence_details && finding.evidence_details.length > 0;

                    return (
                      <Box
                        key={`${finding.rule_id}-${index}`}
                        sx={{
                          p: 3,
                          border: '2px solid',
                          borderColor: finding.status === 'pass' ? 'success.main' : `${statusColor}.main`,
                          borderRadius: 2,
                          borderLeft: '6px solid',
                          borderLeftColor: finding.status === 'pass' ? 'success.main' : `${statusColor}.main`,
                          backgroundColor: finding.status === 'pass' ? 'success.lighter' : `${statusColor}.lighter`,
                          boxShadow: isNeedsReview ? 3 : 1,
                        }}
                      >
                        {/* Rule Title - PRIMARY HEADING (large and prominent) */}
                        <Typography
                          variant="h5"
                          gutterBottom
                          sx={{
                            fontSize: '1.25rem',
                            fontWeight: 700,
                            color: 'text.primary',
                            mb: 0.5,
                            lineHeight: 1.3
                          }}
                        >
                          {finding.title || statusInfo.label}
                        </Typography>

                        {/* Rule description */}
                        {finding.description && (
                          <Typography
                            variant="body2"
                            sx={{
                              color: 'text.secondary',
                              mb: 1.5,
                              fontStyle: 'italic',
                              lineHeight: 1.5
                            }}
                          >
                            {finding.description}
                          </Typography>
                        )}

                        {/* Header with status and rule info (SECONDARY - smaller and less prominent) */}
                        <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                          <Chip
                            label={statusInfo.label}
                            color={statusColor}
                            size="small"
                            icon={finding.status === 'pass' ? <CheckCircle /> : finding.status === 'needs_review' ? <Info /> : <Warning />}
                            sx={{ fontWeight: 600 }}
                          />
                          <Chip
                            label={`Rule: ${finding.rule_id}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem', fontFamily: 'monospace' }}
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

                        {/* Rule Description - What this rule checks */}
                        {ruleDescription && (
                          <Alert severity="info" icon={<Info />} sx={{ mb: 2, bgcolor: 'rgba(33, 150, 243, 0.08)' }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              <strong>What this checks:</strong> {ruleDescription}
                            </Typography>
                          </Alert>
                        )}

                        {/* Main Message */}
                        <Typography variant="body1" sx={{ mb: 2, fontSize: '1rem', lineHeight: 1.6 }}>
                          {finding.message}
                        </Typography>

                        {/* Status Description - Enhanced for needs_review */}
                        {statusInfo.description && isNeedsReview && (
                          <Alert severity="warning" icon={<Info />} sx={{ mb: 2 }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {statusInfo.description}
                            </Typography>
                          </Alert>
                        )}

                        {/* Evidence Details - Collapsible accordion for all cases */}
                        {hasEvidence && (
                          <>
                            {isNeedsReview ? (
                              <EvidenceAccordion 
                                evidence={finding.evidence_details} 
                                defaultExpanded={false}
                                prominent={true}
                              />
                            ) : (
                              <EvidenceAccordion 
                                evidence={finding.evidence_details} 
                                defaultExpanded={false}
                                prominent={false}
                              />
                            )}
                          </>
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
