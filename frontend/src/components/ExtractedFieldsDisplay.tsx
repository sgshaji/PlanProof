import { useState } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  Chip, 
  Tooltip, 
  IconButton,
  Collapse,
  Divider
} from '@mui/material';
import { 
  CheckCircle, 
  Warning, 
  Person,
  Home,
  Straighten,
  Description,
  LocationOn,
  CalendarToday,
  AttachMoney,
  ExpandMore,
  ExpandLess,
  Article,
  ErrorOutline
} from '@mui/icons-material';

interface FieldData {
  value?: any;
  confidence?: number;
  unit?: string;
  field_unit?: string;
  field_value?: any;
  raw_text?: string;
  snippet?: string;
  context?: string;
  page?: number;
  block_id?: string;
  bbox?: any;
  entity?: string;
  datum?: string;
  existing_or_proposed?: string;
}

interface ExtractedFieldsDisplayProps {
  extractedFields: Record<string, FieldData> | Array<{
    field_name: string;
    label?: string;
    value: any;
    formatted_value?: string;
    confidence?: number;
    unit?: string;
  }>;
}

// Human-readable field labels with icons and importance indicators
const FIELD_LABELS: Record<string, { label: string; icon: any; important?: boolean; description?: string }> = {
  application_ref: { label: 'Planning Reference', icon: Description, important: true, description: 'Unique identifier for this application' },
  site_address: { label: 'Property Address', icon: Home, important: true, description: 'Location of the proposed development' },
  postcode: { label: 'Postcode', icon: LocationOn, important: true },
  applicant_name: { label: 'Applicant Name', icon: Person, important: true },
  agent_name: { label: 'Agent Name', icon: Person },
  certificate_type: { label: 'Certificate Type', icon: Article, important: true },
  proposed_use: { label: 'Proposed Use', icon: Description, important: true },
  existing_use: { label: 'Existing Use', icon: Description, important: true },
  development_type: { label: 'Development Type', icon: Description, important: true },
  proposal_description: { label: 'Proposal Description', icon: Description, important: true },
  application_date: { label: 'Application Date', icon: CalendarToday },
  decision_date: { label: 'Decision Date', icon: CalendarToday },
  fee_amount: { label: 'Fee Amount', icon: AttachMoney, important: true },
  floor_area: { label: 'Floor Area', icon: Straighten, important: true },
  site_area: { label: 'Site Area', icon: Straighten, important: true },
  num_dwellings: { label: 'Number of Dwellings', icon: Home },
  num_bedrooms: { label: 'Number of Bedrooms', icon: Home },
  building_height: { label: 'Building Height', icon: Straighten, important: true },
  watercourse_proximity: { label: 'Watercourse Proximity', icon: Straighten, important: true },
  num_parking_spaces: { label: 'Parking Spaces', icon: Home },
  heritage_asset: { label: 'Heritage Asset', icon: Description, important: true },
  listed_building: { label: 'Listed Building', icon: Description, important: true },
  conservation_area: { label: 'Conservation Area', icon: LocationOn, important: true },
  tree_preservation_order: { label: 'Tree Preservation Order', icon: Description, important: true },
  flood_zone: { label: 'Flood Zone', icon: LocationOn, important: true },
  north_arrow_present: { label: 'North Arrow on Plans', icon: Description },
  measurements: { label: 'Measurements', icon: Straighten, description: 'Dimensions extracted from plans' },
};

// Field categories for better organization
const FIELD_CATEGORIES = {
  'Application Details': ['application_ref', 'application_date', 'decision_date', 'certificate_type', 'fee_amount'],
  'Site & Applicant': ['site_address', 'postcode', 'applicant_name', 'agent_name'],
  'Development Details': ['proposed_use', 'existing_use', 'development_type', 'proposal_description', 'floor_area', 'site_area', 'num_dwellings', 'num_bedrooms', 'building_height', 'watercourse_proximity', 'num_parking_spaces'],
  'Constraints': ['heritage_asset', 'listed_building', 'conservation_area', 'tree_preservation_order', 'flood_zone'],
  'Plans & Drawings': ['north_arrow_present', 'measurements'],
};

// Extract the actual value from field data
const extractValue = (fieldData: FieldData): any => {
  // Handle array of objects (like measurements with value, unit, snippet, etc.)
  if (Array.isArray(fieldData)) {
    return fieldData;
  }
  
  // If it's an object with value property
  if (typeof fieldData === 'object' && fieldData !== null) {
    return fieldData.value ?? fieldData.field_value ?? fieldData;
  }
  
  return fieldData;
};

// Format field value for display
const formatFieldValue = (fieldData: FieldData, fieldName: string): string => {
  const value = extractValue(fieldData);
  
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
    
    // For measurements with value and unit
    if (value[0]?.value !== undefined && value[0]?.unit !== undefined) {
      const measurements = value.map(m => {
        const val = `${m.value}${m.unit}`;
        const snippet = m.snippet || m.raw_text;
        if (snippet) {
          // Extract meaningful context from snippet
          const cleanSnippet = snippet.substring(0, 50).trim();
          return `${val} (${cleanSnippet}...)`;
        }
        return val;
      });
      
      if (measurements.length === 1) {
        return measurements[0];
      }
      return `${measurements.length} measurements found`;
    }
    
    // For signatures or other structured arrays
    if (value[0]?.type !== undefined) {
      return `${value.length} ${fieldName} found`;
    }
    
    // Other arrays
    if (value.length <= 3) {
      return value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join(', ');
    }
    return `${value.length} items`;
  }
  
  // Handle objects - try to extract meaningful value
  if (typeof value === 'object') {
    // Check for raw_text first (most readable)
    if (value.raw_text) return value.raw_text;
    if (value.value !== undefined) {
      const val = value.value;
      const unit = value.unit || fieldData.unit || fieldData.field_unit;
      if (unit && typeof val === 'number') {
        return `${val} ${unit}`;
      }
      return String(val);
    }
    // Don't show raw JSON
    return `Complex data (expand to view)`;
  }
  
  // Add unit if present
  const unit = fieldData.unit || fieldData.field_unit;
  if (unit && typeof value === 'number') {
    return `${value} ${unit}`;
  }
  
  return String(value);
};

// Get confidence level and color
const getConfidenceInfo = (confidence?: number): { color: 'success' | 'warning' | 'error' | 'default'; label: string; icon: any } => {
  if (!confidence && confidence !== 0) {
    return { color: 'default', label: 'Unknown', icon: ErrorOutline };
  }
  if (confidence >= 0.8) {
    return { color: 'success', label: `${Math.round(confidence * 100)}% confidence`, icon: CheckCircle };
  }
  if (confidence >= 0.6) {
    return { color: 'warning', label: `${Math.round(confidence * 100)}% confidence`, icon: Warning };
  }
  return { color: 'error', label: `${Math.round(confidence * 100)}% confidence`, icon: ErrorOutline };
};

// Get field label and icon
const getFieldConfig = (fieldName: string) => {
  if (FIELD_LABELS[fieldName]) {
    return FIELD_LABELS[fieldName];
  }
  
  // Generate label from field name
  const label = fieldName
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
  
  return {
    label,
    icon: Description,
    important: false
  };
};

// Field Card Component
function FieldCard({ fieldName, fieldData }: { fieldName: string; fieldData: FieldData }) {
  const [expanded, setExpanded] = useState(false);
  
  const fieldConfig = getFieldConfig(fieldName);
  const displayValue = formatFieldValue(fieldData, fieldName);
  const value = extractValue(fieldData);
  
  // For arrays, get confidence from first item
  let confidence = fieldData.confidence;
  let snippet = fieldData.snippet;
  let page = fieldData.page;
  
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') {
    confidence = confidence || value[0].confidence;
    snippet = snippet || value[0].snippet;
    page = page || value[0].page;
  }
  
  const confidenceInfo = getConfidenceInfo(confidence);
  
  // Check if field has additional context to show
  const hasContext = snippet || fieldData.context || page;
  const IconComponent = fieldConfig.icon;
  
  // Check if this is an array/complex data
  const isArray = Array.isArray(value);
  const hasMultipleItems = isArray && value.length > 0;
  
  return (
    <Grid item xs={12} sm={6} md={4}>
      <Paper
        elevation={2}
        sx={{
          p: 2.5,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          transition: 'all 0.2s',
          '&:hover': {
            boxShadow: 4,
            transform: 'translateY(-2px)',
          },
          borderLeft: fieldConfig.important ? '4px solid' : 'none',
          borderLeftColor: 'primary.main',
        }}
      >
        {/* Header with icon and label */}
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
            <IconComponent sx={{ fontSize: 20, color: 'primary.main' }} />
            <Typography
              variant="subtitle2"
              sx={{
                fontWeight: 600,
                color: 'text.secondary',
                textTransform: 'uppercase',
                fontSize: '0.75rem',
                letterSpacing: '0.5px',
              }}
            >
              {fieldConfig.label}
            </Typography>
          </Box>
          
          {/* Confidence indicator */}
          {confidence !== undefined && confidence !== null && (
            <Tooltip title={confidenceInfo.label} arrow>
              <Chip
                icon={<confidenceInfo.icon sx={{ fontSize: 14 }} />}
                label={`${Math.round(confidence * 100)}%`}
                size="small"
                color={confidenceInfo.color}
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            </Tooltip>
          )}
        </Box>
        
        {/* Main value */}
        <Typography
          variant="body1"
          sx={{
            fontWeight: 500,
            fontSize: '1rem',
            color: displayValue === 'Not specified' ? 'text.secondary' : 'text.primary',
            fontStyle: displayValue === 'Not specified' ? 'italic' : 'normal',
            mb: hasContext ? 1 : 0,
            wordBreak: 'break-word',
          }}
        >
          {displayValue}
        </Typography>
        
        {/* Page reference */}
        {page && (
          <Chip
            label={`📄 Page ${page}`}
            size="small"
            variant="outlined"
            sx={{ alignSelf: 'flex-start', mt: 1, fontSize: '0.7rem' }}
          />
        )}
        
        {/* Expandable context section */}
        {hasContext && (
          <Box sx={{ mt: 'auto', pt: 1.5 }}>
            <Divider sx={{ mb: 1 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Context
              </Typography>
              <IconButton
                size="small"
                onClick={() => setExpanded(!expanded)}
                sx={{ p: 0.5 }}
              >
                {expanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
              </IconButton>
            </Box>
            
            <Collapse in={expanded}>
              <Box sx={{ mt: 1, p: 1.5, bgcolor: 'grey.50', borderRadius: 1 }}>
                {snippet && (
                  <Typography variant="body2" sx={{ fontSize: '0.85rem', lineHeight: 1.5, color: 'text.secondary' }}>
                    "{snippet}"
                  </Typography>
                )}
                
                {/* Technical details */}
                {expanded && (
                  <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      Technical Details:
                    </Typography>
                    {fieldData.entity && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        • Entity: {fieldData.entity}
                      </Typography>
                    )}
                    {fieldData.existing_or_proposed && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        • Type: {fieldData.existing_or_proposed}
                      </Typography>
                    )}
                    {confidence !== undefined && confidence !== null && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        • Confidence: {Math.round(confidence * 100)}%
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
            </Collapse>
          </Box>
        )}
        
        {/* Show array items if expanded */}
        {hasMultipleItems && expanded && (
          <Box sx={{ mt: 1.5, p: 1.5, bgcolor: 'grey.50', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
            {value.slice(0, 10).map((item: any, idx: number) => (
              <Box key={idx} sx={{ mb: 1, pb: 1, borderBottom: idx < Math.min(value.length, 10) - 1 ? '1px solid' : 'none', borderColor: 'divider' }}>
                {typeof item === 'object' ? (
                  <Box>
                    {item.value && item.unit && (
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {item.value} {item.unit}
                      </Typography>
                    )}
                    {item.snippet && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                        "{item.snippet.substring(0, 100)}{item.snippet.length > 100 ? '...' : ''}"
                      </Typography>
                    )}
                    {item.page && (
                      <Typography variant="caption" color="primary.main" sx={{ display: 'block', mt: 0.5 }}>
                        📄 Page {item.page}
                      </Typography>
                    )}
                  </Box>
                ) : (
                  <Typography variant="body2">{String(item)}</Typography>
                )}
              </Box>
            ))}
            {value.length > 10 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
                ... and {value.length - 10} more items
              </Typography>
            )}
          </Box>
        )}
      </Paper>
    </Grid>
  );
}

// Parse Python string representation to JSON
const parsePythonString = (str: string): any => {
  try {
    // Replace Python None with null
    let jsonStr = str.replace(/None/g, 'null');
    // Replace Python True/False with true/false
    jsonStr = jsonStr.replace(/True/g, 'true').replace(/False/g, 'false');
    // Replace single quotes with double quotes (carefully)
    jsonStr = jsonStr.replace(/'/g, '"');
    return JSON.parse(jsonStr);
  } catch (e) {
    console.warn('Failed to parse Python string:', e);
    return str;
  }
};

// Normalize extracted fields to dictionary format
const normalizeExtractedFields = (fields: any): Record<string, FieldData> => {
  // If it's already an object/dictionary, return as is
  if (!Array.isArray(fields)) {
    return fields;
  }
  
  // Convert array format to dictionary format
  const normalized: Record<string, FieldData> = {};
  fields.forEach((field: any) => {
    const fieldName = field.field_name;
    let value = field.value;
    
    // Try to parse string values that look like Python lists/dicts
    if (typeof value === 'string' && (value.startsWith('[') || value.startsWith('{'))) {
      value = parsePythonString(value);
    }
    
    normalized[fieldName] = {
      value,
      confidence: field.confidence,
      unit: field.unit,
      field_value: value,
    };
  });
  
  return normalized;
};

export default function ExtractedFieldsDisplay({ extractedFields }: ExtractedFieldsDisplayProps) {
  // Normalize the data format
  const normalizedFields = normalizeExtractedFields(extractedFields);
  
  // Group fields by category
  const categorizedFields: Record<string, Record<string, FieldData>> = {};
  const uncategorizedFields: Record<string, FieldData> = {};
  
  Object.entries(normalizedFields).forEach(([fieldName, fieldData]) => {
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

  return (
    <Box>
      {/* Categorized fields */}
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
            <Chip label={Object.keys(fields).length} size="small" color="primary" />
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(fields).map(([fieldName, fieldData]) => (
              <FieldCard key={fieldName} fieldName={fieldName} fieldData={fieldData} />
            ))}
          </Grid>
        </Box>
      ))}
      
      {/* Uncategorized fields */}
      {Object.keys(uncategorizedFields).length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography 
            variant="h6" 
            sx={{ 
              mb: 2, 
              fontWeight: 600, 
              color: 'text.secondary',
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
          >
            Other Fields
            <Chip label={Object.keys(uncategorizedFields).length} size="small" />
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(uncategorizedFields).map(([fieldName, fieldData]) => (
              <FieldCard key={fieldName} fieldName={fieldName} fieldData={fieldData} />
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  );
}
