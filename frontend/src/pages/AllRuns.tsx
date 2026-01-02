import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  CircularProgress,
  Alert,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
} from '@mui/material';
import { Refresh } from '@mui/icons-material';
import { api } from '../api/client';
import type { Run } from '../types';

export default function AllRuns() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const loadRuns = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getRuns(1, 50, statusFilter === 'all' ? undefined : statusFilter);
      // API returns direct array, not wrapped object
      setRuns(Array.isArray(data) ? data : (data.runs || []));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load runs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [statusFilter]);

  const filteredRuns = runs.filter((run) =>
    searchQuery === '' ||
    run.id.toString().includes(searchQuery) ||
    run.application_ref?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">
          🔍 All Validation Runs
        </Typography>
        <Button startIcon={<Refresh />} onClick={loadRuns}>
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <TextField
            fullWidth
            placeholder="Search by run ID or application reference..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth size="small">
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
            </Select>
          </FormControl>
        </Grid>
      </Grid>

      {/* Runs List */}
      {filteredRuns.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" color="text.secondary">
              📋 No Runs Found
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {filteredRuns.map((run) => (
            <Grid item xs={12} key={run.id}>
              <Card>
                <CardContent>
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} md={3}>
                      <Typography variant="h6">Run #{run.id}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {run.run_type}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        {run.application_ref || 'N/A'}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Chip
                        label={run.status}
                        color={
                          run.status === 'completed'
                            ? 'success'
                            : run.status === 'running'
                            ? 'info'
                            : 'error'
                        }
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(run.started_at).toLocaleString()}
                      </Typography>
                    </Grid>
                  </Grid>
                  {run.error_message && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                      {run.error_message}
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
