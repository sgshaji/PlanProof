import { Box, Typography, Grid, Paper, Chip, Tooltip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Alert } from '@mui/material';
import { CheckCircle, HelpOutline, Warning, Star, Info } from '@mui/icons-material';

interface FieldData {
  value?: any;
  confidence?: number;
  unit?: string;
  field_unit?: string;
  field_value?: any;
}

interface ExtractedFieldsDisplayProps {
  extractedFields: Record<string, FieldData>;
}

// Human-readable field labels with importance indicators
const FIELD_LABELS: Record<string, { label: string; important?: boolean; description?: string }> = {
  application_ref: { label: 'Application Reference', important: true, description: 'Unique identifier for this application' },
  site_address: { label: 'Site Address', important: true, description: 'Location of the proposed development' },
  postcode: { label: 'Postcode', important: true },
  applicant_name: { label: 'Applicant Name', important: true },
  agent_name: { label: 'Agent Name' },
  certificate_type: { label: 'Certificate Type', important: true },
  proposed_use: { label: 'Proposed Use', important: true },
  existing_use: { label: 'Existing Use', important: true },
  development_type: { label: 'Development Type', important: true },
  proposal_description: { label: 'Proposal Description', important: true },
  application_date: { label: 'Application Date' },
  decision_date: { label: 'Decision Date' },
  fee_amount: { label: 'Fee Amount', important: true },
  floor_area: { label: 'Floor Area', important: true },
  site_area: { label: 'Site Area', important: true },
  num_dwellings: { label: 'Number of Dwellings' },
  num_bedrooms: { label: 'Number of Bedrooms' },
  building_height: { label: 'Building Height', important: true },
  num_parking_spaces: { label: 'Parking Spaces' },
  heritage_asset: { label: 'Heritage Asset', important: true },
  listed_building: { label: 'Listed Building', important: true },
  conservation_area: { label: 'Conservation Area', important: true },
  tree_preservation_order: { label: 'Tree Preservation Order', important: true },
  flood_zone: { label: 'Flood Zone', important: true },
  north_arrow_present: { label: 'North Arrow on Plans' },
  measurements: { label: 'Measurements', description: 'Dimensions extracted from plans' },
};

// Field categories for better organization
const FIELD_CATEGORIES = {
  'Application Details': ['application_ref', 'application_date', 'decision_date', 'certificate_type', 'fee_amount'],
  'Site & Applicant': ['site_address', 'postcode', 'applicant_name', 'agent_name'],
  'Development Details': ['proposed_use', 'existing_use', 'development_type', 'proposal_description', 'floor_area', 'site_area', 'num_dwellings', 'num_bedrooms', 'building_height', 'num_parking_spaces'],
  'Constraints': ['heritage_asset', 'listed_building', 'conservation_area', 'tree_preservation_order', 'flood_zone'],
  'Plans & Drawings': ['north_arrow_present', 'measurements'],
};

const formatFieldValue = (fieldData: FieldData): { display: string; isComplex: boolean; complexData?: any } => {
  let value = fieldData.value ?? fieldData.field_value;

  // Handle null/undefined
  if (value === null || value === undefined || value === '') {
    return { display: 'Not specified', isComplex: false };
  }

  // Handle boolean
  if (typeof value === 'boolean') {
    return { display: value ? 'Yes' : 'No', isComplex: false };
  }

  // Handle arrays (like measurements)
  if (Array.isArray(value)) {
    if (value.length === 0) return { display: 'None found', isComplex: false };

    // For measurements, show readable summary and mark as complex
    const measurements = value as any[];
    if (measurements[0]?.value !== undefined && measurements[0]?.unit !== undefined) {
      const summary = measurements.map(m => `${m.value}${m.unit}`).slice(0, 2).join(', ');
      return {
        display: `${measurements.length} measurement${measurements.length > 1 ? 's' : ''}`,
        isComplex: true,
        complexData: measurements
      };
    }

    // Other arrays
    if (value.length <= 3) {
      return { display: value.join(', '), isComplex: false };
    }
    return {
      display: `${value.length} items`,
      isComplex: true,
      complexData: value
    };
  }

  // Handle objects - mark as complex
  if (typeof value === 'object') {
    const keys = Object.keys(value);
    return {
      display: `${keys.length} properties`,
      isComplex: true,
      complexData: value
    };
  }

  // Add unit if present
  const unit = fieldData.unit || fieldData.field_unit;
  if (unit && typeof value === 'number') {
    return { display: `${value} ${unit}`, isComplex: false };
  }

  return { display: String(value), isComplex: false };
};

// Render complex data in a readable format
const renderComplexData = (data: any, fieldName: string) => {
  // Handle measurements array
  if (Array.isArray(data) && data[0]?.value !== undefined && data[0]?.unit !== undefined) {
    return (
      <TableContainer component={Paper} variant="outlined" sx={{ mt: 1.5, maxHeight: 300 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Value</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Unit</TableCell>
              {data[0]?.label && <TableCell sx={{ fontWeight: 600 }}>Label</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {data.slice(0, 10).map((item: any, idx: number) => (
              <TableRow key={idx}>
                <TableCell>{item.value}</TableCell>
                <TableCell>{item.unit}</TableCell>
                {item.label && <TableCell>{item.label}</TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {data.length > 10 && (
          <Alert severity="info" sx={{ borderRadius: 0 }}>
            Showing 10 of {data.length} measurements
          </Alert>
        )}
      </TableContainer>
    );
  }

  // Handle regular arrays
  if (Array.isArray(data)) {
    return (
      <Box sx={{ mt: 1.5 }}>
        {data.slice(0, 10).map((item: any, idx: number) => (
          <Chip
            key={idx}
            label={typeof item === 'object' ? JSON.stringify(item) : String(item)}
            size="small"
            sx={{ mr: 0.5, mb: 0.5 }}
          />
        ))}
        {data.length > 10 && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            ... and {data.length - 10} more
          </Typography>
        )}
      </Box>
    );
  }

  // Handle objects
  if (typeof data === 'object') {
    return (
      <Box sx={{ mt: 1.5, p: 1.5, bgcolor: 'grey.50', borderRadius: 1, fontFamily: 'monospace', fontSize: '0.85rem' }}>
        {Object.entries(data).slice(0, 5).map(([key, val]) => (
          <Box key={key} sx={{ mb: 0.5 }}>
            <Typography component="span" sx={{ fontWeight: 600, color: 'primary.main' }}>
              {key}:
            </Typography>{' '}
            <Typography component="span" color="text.secondary">
              {typeof val === 'object' ? JSON.stringify(val) : String(val)}
            </Typography>
          </Box>
        ))}
        {Object.keys(data).length > 5 && (
          <Typography variant="caption" color="text.secondary">
            ... {Object.keys(data).length - 5} more properties
          </Typography>
        )}
      </Box>
    );
  }

  return null;
};

const getConfidenceColor = (confidence?: number): 'success' | 'warning' | 'error' | 'default' => {
  if (!confidence) return 'default';
  if (confidence >= 0.8) return 'success';
  if (confidence >= 0.6) return 'warning';
  return 'error';
};

const getConfidenceIcon = (confidence?: number) => {
  if (!confidence) return <HelpOutline fontSize="small" />;
  if (confidence >= 0.8) return <CheckCircle fontSize="small" />;
  return <Warning fontSize="small" />;
};

export default function ExtractedFieldsDisplay({ extractedFields }: ExtractedFieldsDisplayProps) {
  // Group fields by category
  const categorizedFields: Record<string, Record<string, FieldData>> = {};
  const uncategorizedFields: Record<string, FieldData> = {};
  
  Object.entries(extractedFields).forEach(([fieldName, fieldData]) => {
    let found = false;
    for (const [category, fields] of Object.entries(FIELD_CATEGORIES)) {
      if (fields.includes(fieldName)) {
        if (!categorizedFields[category]) {
          categorizedFields[category] = {};
        }
        categorizedFields[category][fieldName] = fieldData;
        found = true;
        break;
      }
    }
    if (!found) {
      uncategorizedFields[fieldName] = fieldData;
    }
  });

  const renderFieldCard = (fieldName: string, fieldData: FieldData) => {
    const fieldConfig = FIELD_LABELS[fieldName] || {
      label: fieldName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      important: false
    };
    const formatted = formatFieldValue(fieldData);
    const confidence = fieldData.confidence;
    const isImportant = fieldConfig.important;

    return (
      <Grid item xs={12} sm={6} md={isImportant ? 6 : 4} key={fieldName}>
        <Paper
          variant="outlined"
          sx={{
            p: 2.5,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            transition: 'all 0.2s',
            borderWidth: isImportant ? 2 : 1,
            borderColor: isImportant ? 'primary.main' : 'divider',
            bgcolor: isImportant ? 'primary.lighter' : 'background.paper',
            '&:hover': {
              boxShadow: 3,
              transform: 'translateY(-2px)',
            }
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {isImportant && (
                <Tooltip title="Key field">
                  <Star sx={{ fontSize: 14, color: 'primary.main' }} />
                </Tooltip>
              )}
              <Tooltip title={fieldConfig.description || ''} arrow>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    textTransform: 'uppercase',
                    fontWeight: 600,
                    letterSpacing: '0.5px',
                    fontSize: isImportant ? '0.75rem' : '0.7rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    cursor: fieldConfig.description ? 'help' : 'default'
                  }}
                >
                  {fieldConfig.label}
                  {fieldConfig.description && <Info sx={{ fontSize: 12 }} />}
                </Typography>
              </Tooltip>
            </Box>
          </Box>

          <Typography
            variant="body1"
            sx={{
              mt: 'auto',
              fontWeight: isImportant ? 600 : 500,
              fontSize: isImportant ? '1.1rem' : '1rem',
              color: formatted.display === 'Not specified' ? 'text.secondary' : 'text.primary',
              fontStyle: formatted.display === 'Not specified' ? 'italic' : 'normal',
            }}
          >
            {formatted.display}
          </Typography>

          {/* Show complex data if present */}
          {formatted.isComplex && formatted.complexData && (
            <Box sx={{ mt: 2 }}>
              {renderComplexData(formatted.complexData, fieldName)}
            </Box>
          )}
        </Paper>
      </Grid>
    );
  };

  return (
    <Box>
      {Object.entries(categorizedFields).map(([category, fields]) => (
        <Box key={category} sx={{ mb: 4 }}>
          <Typography 
            variant="h6" 
            sx={{ 
              mb: 2, 
              fontWeight: 600,
              color: 'primary.main',
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
          >
            {category}
            <Chip label={Object.keys(fields).length} size="small" />
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(fields).map(([fieldName, fieldData]) => renderFieldCard(fieldName, fieldData))}
          </Grid>
        </Box>
      ))}
      
      {Object.keys(uncategorizedFields).length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
            Other Fields
            <Chip label={Object.keys(uncategorizedFields).length} size="small" sx={{ ml: 1 }} />
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(uncategorizedFields).map(([fieldName, fieldData]) => renderFieldCard(fieldName, fieldData))}
          </Grid>
        </Box>
      )}
    </Box>
  );
}
