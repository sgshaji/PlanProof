import { useState, useEffect } from 'react';
import { Box, Card, CardContent, Grid, Typography, Skeleton } from '@mui/material';
import { api } from '../api/client';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalApplications: 0,
    completed: 0,
    inProgress: 0,
    failed: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [applications, runs] = await Promise.all([
          api.getApplications(1, 100),
          api.getRuns(1, 100)
        ]);
        
        const apps = Array.isArray(applications) ? applications : [];
        const runsData = Array.isArray(runs) ? runs : [];
        
        setStats({
          totalApplications: apps.length,
          completed: runsData.filter(r => r.status === 'completed').length,
          inProgress: runsData.filter(r => r.status === 'running').length,
          failed: runsData.filter(r => r.status === 'failed').length
        });
      } catch (err) {
        console.error('Failed to load stats:', err);
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, []);

  if (loading) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom fontWeight="bold">
          📊 Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={3}>
          Analytics and insights
        </Typography>
        <Grid container spacing={3}>
          {Array.from({ length: 4 }).map((_, index) => (
            <Grid item xs={12} md={3} key={index}>
              <Card>
                <CardContent>
                  <Skeleton variant="text" width="40%" height={40} />
                  <Skeleton variant="text" width="60%" />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Skeleton variant="text" width="30%" />
            <Skeleton variant="text" width="60%" />
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight="bold">
        📊 Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={3}>
        Analytics and insights
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="primary">
                {stats.totalApplications}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Applications
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="success.main">
                {stats.completed}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="warning.main">
                {stats.inProgress}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                In Progress
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="error.main">
                {stats.failed}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Issues Found
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No recent activity
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
