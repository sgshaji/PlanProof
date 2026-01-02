import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  CircularProgress,
  Alert,
  Skeleton,
  Stack,
} from '@mui/material';
import { Visibility, Refresh } from '@mui/icons-material';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errorUtils';

export default function MyCases() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const pageSize = 20;

  const loadCases = async (pageToLoad = 1, replace = false) => {
    if (replace) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    setError('');
    try {
      const data = await api.getApplications(pageToLoad, pageSize);
      // API returns direct array, not wrapped object
      const incomingCases = Array.isArray(data) ? data : (data.applications || []);
      setCases((prev) => (replace ? incomingCases : [...prev, ...incomingCases]));
      setHasMore(incomingCases.length === pageSize);
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Failed to load cases'));
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    loadCases(page, page === 1);
  }, [page]);

  const handleRefresh = () => {
    setPage(1);
    if (page === 1) {
      loadCases(1, true);
    }
  };

  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      setPage((prev) => prev + 1);
    }
  };

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      searchQuery === '' ||
      c.application_ref?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.applicant_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">
          📋 My Cases
        </Typography>
        <Button startIcon={<Refresh />} onClick={handleRefresh}>
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
            placeholder="Search by reference or applicant name..."
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
              <MenuItem value="completed">Complete</MenuItem>
              <MenuItem value="processing">Processing</MenuItem>
              <MenuItem value="issues">Issues Found</MenuItem>
            </Select>
          </FormControl>
        </Grid>
      </Grid>

      {/* Cases List */}
      {loading && cases.length === 0 ? (
        <Stack spacing={2}>
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <Box sx={{ flex: 1 }}>
                    <Skeleton variant="text" width="40%" height={28} />
                    <Skeleton variant="text" width="30%" />
                    <Skeleton variant="text" width="25%" />
                    <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                      <Skeleton variant="rounded" width={90} height={24} />
                      <Skeleton variant="rounded" width={120} height={24} />
                    </Box>
                  </Box>
                  <Skeleton variant="rounded" width={120} height={36} />
                </Box>
              </CardContent>
            </Card>
          ))}
        </Stack>
      ) : filteredCases.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              📋 No Applications Found
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={3}>
              {searchQuery || statusFilter !== 'all'
                ? 'No applications match your filters'
                : 'Upload your first planning application to get started'}
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/new-application')}
            >
              Create New Application
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <Grid container spacing={2}>
            {filteredCases.map((caseItem) => (
              <Grid item xs={12} key={caseItem.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" gutterBottom>
                          {caseItem.application_ref}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {caseItem.applicant_name || 'Unknown'}
                        </Typography>
                        {caseItem.run_count > 0 && (
                          <Typography variant="body2" color="text.secondary">
                            {caseItem.run_count} run{caseItem.run_count !== 1 ? 's' : ''} processed
                          </Typography>
                        )}
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                          <Chip
                            label={caseItem.status || 'Unknown'}
                            color={
                              caseItem.status === 'completed'
                                ? 'success'
                                : caseItem.status === 'processing'
                                ? 'info'
                                : 'error'
                            }
                            size="small"
                          />
                          <Chip
                            label={`📅 ${new Date(caseItem.created_at).toLocaleDateString()}`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </Box>
                      <Button
                        variant="outlined"
                        startIcon={<Visibility />}
                        onClick={() => navigate(`/applications/${caseItem.id}`)}
                      >
                        Open Case
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
          {hasMore && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
              <Button
                variant="outlined"
                onClick={handleLoadMore}
                disabled={loadingMore}
                startIcon={loadingMore ? <CircularProgress size={16} /> : undefined}
              >
                {loadingMore ? 'Loading more cases...' : 'Load more cases'}
              </Button>
            </Box>
          )}
        </>
      )}
    </Box>
  );
}
