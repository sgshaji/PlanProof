import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Alert,
  CircularProgress,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Paper,
} from '@mui/material';
import {
  ExpandMore,
  Psychology,
  Code,
  Info,
  ContentCopy,
} from '@mui/icons-material';
import { api } from '../api/client';

interface LLMCall {
  id: string;
  timestamp: string;
  prompt: string;
  response: string;
  model: string;
  tokens_used?: number;
  cost?: number;
  purpose: string;
}

interface LLMTransparencyProps {
  runId: number;
}

const LLMTransparency: React.FC<LLMTransparencyProps> = ({ runId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [llmCalls, setLlmCalls] = useState<LLMCall[]>([]);
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalCost, setTotalCost] = useState(0);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    loadLLMCalls();
  }, [runId]);

  const loadLLMCalls = async () => {
    setLoading(true);
    setError(null);

    try {
      // TODO: Implement API endpoint to retrieve LLM call logs
      // For now, show placeholder
      setError('LLM call transparency endpoint not yet implemented');
      setLoading(false);
      
      // Mock data for demonstration
      // const response = await api.getLLMCalls(runId);
      // setLlmCalls(response.llm_calls);
      // setTotalTokens(response.total_tokens);
      // setTotalCost(response.total_cost);
      // setLoading(false);
    } catch (err: any) {
      console.error('Failed to load LLM calls:', err);
      setError(err.message || 'Failed to load LLM transparency data');
      setLoading(false);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatCost = (cost: number) => {
    return `$${cost.toFixed(4)}`;
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <CircularProgress size={24} />
            <Typography>Loading LLM transparency data...</Typography>
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
              To enable LLM transparency, implement GET /api/v1/runs/{'{'}runId{'}'}/llm-calls endpoint
              that retrieves stored LLM interaction logs from blob storage.
            </Typography>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Psychology color="primary" />
          <Typography variant="h6">LLM Call Transparency</Typography>
          <Chip
            label={`${llmCalls.length} calls`}
            size="small"
            color="primary"
            variant="outlined"
          />
        </Box>

        {/* Summary Stats */}
        <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
          <Stack direction="row" spacing={3} divider={<Divider orientation="vertical" flexItem />}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Total Tokens
              </Typography>
              <Typography variant="h6">{totalTokens.toLocaleString()}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Total Cost
              </Typography>
              <Typography variant="h6">{formatCost(totalCost)}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Avg Tokens/Call
              </Typography>
              <Typography variant="h6">
                {llmCalls.length > 0 ? Math.round(totalTokens / llmCalls.length).toLocaleString() : 0}
              </Typography>
            </Box>
          </Stack>
        </Paper>

        {/* Individual LLM Calls */}
        {llmCalls.length === 0 ? (
          <Alert severity="info">
            No LLM calls were made during this validation run.
          </Alert>
        ) : (
          <Stack spacing={1}>
            {llmCalls.map((call) => (
              <Accordion key={call.id}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <Code fontSize="small" color="action" />
                    <Typography variant="body2" sx={{ flexGrow: 1 }}>
                      {call.purpose}
                    </Typography>
                    <Chip label={call.model} size="small" variant="outlined" />
                    {call.tokens_used && (
                      <Chip
                        label={`${call.tokens_used} tokens`}
                        size="small"
                        color="default"
                      />
                    )}
                    {call.cost && (
                      <Chip
                        label={formatCost(call.cost)}
                        size="small"
                        color="success"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={2}>
                    {/* Timestamp */}
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Timestamp: {new Date(call.timestamp).toLocaleString()}
                      </Typography>
                    </Box>

                    {/* Prompt */}
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2" fontWeight="600">
                          Prompt
                        </Typography>
                        <Tooltip title={copiedId === `prompt-${call.id}` ? 'Copied!' : 'Copy prompt'}>
                          <IconButton
                            size="small"
                            onClick={() => handleCopy(call.prompt, `prompt-${call.id}`)}
                          >
                            <ContentCopy fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      <Paper
                        variant="outlined"
                        sx={{
                          p: 2,
                          bgcolor: 'grey.50',
                          maxHeight: 300,
                          overflow: 'auto',
                        }}
                      >
                        <Typography
                          variant="body2"
                          component="pre"
                          sx={{
                            fontFamily: 'monospace',
                            fontSize: '0.85rem',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            m: 0,
                          }}
                        >
                          {call.prompt}
                        </Typography>
                      </Paper>
                    </Box>

                    {/* Response */}
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2" fontWeight="600">
                          Response
                        </Typography>
                        <Tooltip title={copiedId === `response-${call.id}` ? 'Copied!' : 'Copy response'}>
                          <IconButton
                            size="small"
                            onClick={() => handleCopy(call.response, `response-${call.id}`)}
                          >
                            <ContentCopy fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      <Paper
                        variant="outlined"
                        sx={{
                          p: 2,
                          bgcolor: 'success.50',
                          maxHeight: 300,
                          overflow: 'auto',
                        }}
                      >
                        <Typography
                          variant="body2"
                          component="pre"
                          sx={{
                            fontFamily: 'monospace',
                            fontSize: '0.85rem',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            m: 0,
                          }}
                        >
                          {call.response}
                        </Typography>
                      </Paper>
                    </Box>
                  </Stack>
                </AccordionDetails>
              </Accordion>
            ))}
          </Stack>
        )}

        {/* Info Note */}
        <Alert severity="info" icon={<Info />} sx={{ mt: 2 }}>
          <Typography variant="caption">
            LLM calls are logged for transparency and debugging. All prompts and responses are stored securely
            and can be reviewed for quality assurance and model performance analysis.
          </Typography>
        </Alert>
      </CardContent>
    </Card>
  );
};

export default LLMTransparency;
