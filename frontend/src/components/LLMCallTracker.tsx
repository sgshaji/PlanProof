import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Switch,
  FormControlLabel
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

interface LLMCall {
  timestamp: string;
  purpose: string;
  rule_type: string;
  tokens_used: number;
  model: string;
  response_time_ms: number;
}

interface LLMCallTrackerProps {
  calls: LLMCall[];
  totalTokens: number;
  totalCalls: number;
  showDetails?: boolean;
}

const LLMCallTracker: React.FC<LLMCallTrackerProps> = ({
  calls,
  totalTokens,
  totalCalls,
  showDetails = false
}) => {
  const [expanded, setExpanded] = useState(showDetails);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Accordion expanded={expanded} onChange={handleToggle}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="llm-calls-content"
          id="llm-calls-header"
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
            <Typography variant="h6">LLM Call Statistics</Typography>
            <Chip label={`${totalCalls} calls`} color="primary" size="small" />
            <Chip label={`${totalTokens.toLocaleString()} tokens`} color="secondary" size="small" />
            <FormControlLabel
              control={
                <Switch
                  checked={expanded}
                  onClick={(e) => e.stopPropagation()}
                  size="small"
                  aria-label="Toggle detailed LLM call statistics"
                />
              }
              label="Show Details"
              onClick={(e) => e.stopPropagation()}
              sx={{ ml: 'auto' }}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {calls.length === 0 ? (
            <Typography color="text.secondary">No LLM calls recorded for this review.</Typography>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small" aria-label="LLM call details">
                <TableHead>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Purpose</TableCell>
                    <TableCell>Rule Type</TableCell>
                    <TableCell>Model</TableCell>
                    <TableCell align="right">Tokens Used</TableCell>
                    <TableCell align="right">Response Time (ms)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {calls.map((call, index) => (
                    <TableRow
                      key={index}
                      sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                    >
                      <TableCell component="th" scope="row">
                        {new Date(call.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>{call.purpose}</TableCell>
                      <TableCell>
                        <Chip label={call.rule_type} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>{call.model}</TableCell>
                      <TableCell align="right">{call.tokens_used.toLocaleString()}</TableCell>
                      <TableCell align="right">{call.response_time_ms}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default LLMCallTracker;
