import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Typography,
  Tooltip,
  alpha,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';

interface ExtractedField {
  field_name: string;
  label: string;
  value: any;
  formatted_value: string;
  confidence: number;
  confidence_label: string;
  extractor: string;
  unit?: string;
}

interface ExtractedFieldsDisplayProps {
  fields: ExtractedField[];
}

const ExtractedFieldsDisplay: React.FC<ExtractedFieldsDisplayProps> = ({ fields }) => {
  if (!fields || fields.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
        <Typography>No extracted fields available</Typography>
      </Box>
    );
  }

  const getConfidenceColor = (confidenceLabel: string) => {
    switch (confidenceLabel) {
      case 'High':
        return 'success';
      case 'Medium':
        return 'warning';
      case 'Low':
        return 'error';
      default:
        return 'default';
    }
  };

  const getConfidenceIcon = (confidenceLabel: string) => {
    switch (confidenceLabel) {
      case 'High':
        return <CheckCircleIcon fontSize="small" />;
      case 'Medium':
        return <WarningIcon fontSize="small" />;
      case 'Low':
        return <ErrorIcon fontSize="small" />;
      default:
        return null;
    }
  };

  return (
    <Grid container spacing={2}>
      {fields.map((field) => (
        <Grid item xs={12} sm={6} md={4} key={field.field_name}>
          <Card
            variant="outlined"
            sx={{
              height: '100%',
              borderColor: alpha('#1976d2', 0.2),
              transition: 'all 0.2s',
              '&:hover': {
                borderColor: '#1976d2',
                boxShadow: 2,
                transform: 'translateY(-2px)',
              },
            }}
          >
            <CardContent>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: 'block',
                  mb: 0.5,
                  textTransform: 'uppercase',
                  fontWeight: 600,
                  letterSpacing: 0.5,
                }}
              >
                {field.label}
              </Typography>

              <Typography
                variant="body1"
                sx={{
                  mb: 1.5,
                  fontWeight: 500,
                  minHeight: 48,
                  display: 'flex',
                  alignItems: 'center',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {field.formatted_value}
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                <Tooltip title={`Confidence: ${(field.confidence * 100).toFixed(0)}%`}>
                  <Chip
                    icon={getConfidenceIcon(field.confidence_label)}
                    label={field.confidence_label}
                    size="small"
                    color={getConfidenceColor(field.confidence_label)}
                    variant="outlined"
                  />
                </Tooltip>

                <Tooltip title={`Extracted by: ${field.extractor}`}>
                  <Chip
                    label={field.extractor.toUpperCase()}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.7rem' }}
                  />
                </Tooltip>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default ExtractedFieldsDisplay;
