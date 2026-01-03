import { Box, Typography, Grid, Paper, Chip, Tooltip } from '@mui/material';
import { CheckCircle, HelpOutline, Warning } from '@mui/icons-material';

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

// Human-readable field labels
const FIELD_LABELS: Record<string, string> = {
  application_ref: 'Application Reference',
  site_address: 'Site Address',
  postcode: 'Postcode',
  applicant_name: 'Applicant Name',
  agent_name: 'Agent Name',
  certificate_type: 'Certificate Type',
  proposed_use: 'Proposed Use',
  existing_use: 'Existing Use',
  development_type: 'Development Type',
  proposal_description: 'Proposal Description',
  application_date: 'Application Date',
  decision_date: 'Decision Date',
  fee_amount: 'Fee Amount',
  floor_area: 'Floor Area',
  site_area: 'Site Area',
  num_dwellings: 'Number of Dwellings',
  num_bedrooms: 'Number of Bedrooms',
  building_height: 'Building Height',
  num_parking_spaces: 'Parking Spaces',
  heritage_asset: 'Heritage Asset',
  listed_building: 'Listed Building',
  conservation_area: 'Conservation Area',
  tree_preservation_order: 'Tree Preservation Order',
  flood_zone: 'Flood Zone',
  north_arrow_present: 'North Arrow on Plans',
  measurements: 'Measurements',
};

// Field categories for better organization
const FIELD_CATEGORIES = {
  'Application Details': ['application_ref', 'application_date', 'decision_date', 'certificate_type', 'fee_amount'],
  'Site & Applicant': ['site_address', 'postcode', 'applicant_name', 'agent_name'],
  'Development Details': ['proposed_use', 'existing_use', 'development_type', 'proposal_description', 'floor_area', 'site_area', 'num_dwellings', 'num_bedrooms', 'building_height', 'num_parking_spaces'],
  'Constraints': ['heritage_asset', 'listed_building', 'conservation_area', 'tree_preservation_order', 'flood_zone'],
  'Plans & Drawings': ['north_arrow_present', 'measurements'],
};

const formatFieldValue = (fieldData: FieldData): string => {
  let value = fieldData.value ?? fieldData.field_value;
  
  // Handle null/undefined
  if (value === null || value === undefined || value === '') {
    return 'Not specified';
  }
  
  // Handle boolean
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  
  // Handle arrays (like measurements)
  if (Array.isArray(value)) {
    if (value.length === 0) return 'None found';
    
    // For measurements, show readable summary
    const measurements = value as any[];
    if (measurements[0]?.value !== undefined && measurements[0]?.unit !== undefined) {
      const summary = measurements.map(m => `${m.value}${m.unit}`).slice(0, 3).join(', ');
      if (measurements.length > 3) {
        return `${measurements.length} measurements: ${summary}...`;
      }
      return `${measurements.length} measurement${measurements.length > 1 ? 's' : ''}: ${summary}`;
    }
    
    return `${value.length} items`;
  }
  
  // Handle objects - show friendly summary instead of JSON
  if (typeof value === 'object') {
    return 'Complex data (see details below)';
  }
  
  // Add unit if present
  const unit = fieldData.unit || fieldData.field_unit;
  if (unit && typeof value === 'number') {
    return `${value} ${unit}`;
  }
  
  return String(value);
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
    const label = FIELD_LABELS[fieldName] || fieldName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    const formattedValue = formatFieldValue(fieldData);
    const confidence = fieldData.confidence;

    return (
      <Grid item xs={12} sm={6} md={4} key={fieldName}>
        <Paper 
          variant="outlined" 
          sx={{ 
            p: 2.5, 
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            transition: 'all 0.2s',
            '&:hover': {
              boxShadow: 2,
              transform: 'translateY(-2px)',
            }
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
            <Typography 
              variant="caption" 
              color="text.secondary" 
              sx={{ 
                textTransform: 'uppercase', 
                fontWeight: 600,
                letterSpacing: '0.5px',
                fontSize: '0.7rem'
              }}
            >
              {label}
            </Typography>
          </Box>
          
          <Typography 
            variant="body1" 
            sx={{ 
              mt: 'auto',
              fontWeight: 500,
              color: formattedValue === 'Not specified' ? 'text.secondary' : 'text.primary',
              fontStyle: formattedValue === 'Not specified' ? 'italic' : 'normal',
            }}
          >
            {formattedValue}
          </Typography>
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
