/**
 * Dashboard page - Main landing page with stats and recent jobs
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Skeleton,
  Alert,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  PlayArrow as StartIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingIcon,
  DataUsage as DataIcon,
  Assessment as JobsIcon,
} from '@mui/icons-material';
import type { DashboardStats, Job } from '../types';
import { getJobs, getMetrics } from '../services/api';

// StatCard component - defined outside Dashboard to prevent re-creation on render
interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color, loading }) => (
  <Card elevation={2}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <Box>
          <Typography color="textSecondary" gutterBottom variant="overline">
            {title}
          </Typography>
          <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
            {loading ? <Skeleton width={60} /> : value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="textSecondary">
              {loading ? <Skeleton width={80} /> : subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            p: 1.5,
            borderRadius: 2,
            bgcolor: `${color}.light`,
            color: `${color}.dark`,
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch dashboard data function
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch recent jobs
      const jobsResponse = await getJobs(1, 10);
      const recentJobs = jobsResponse.items;

      // Calculate stats
      const completedJobs = recentJobs.filter((job) => job.status === 'completed');
      const totalJobs = recentJobs.length;
      
      // Calculate average accuracy from metrics
      let totalAccuracy = 0;
      let accuracyCount = 0;

      for (const job of completedJobs) {
        try {
          const metrics = await getMetrics(job.datasetId);
          if (metrics.accuracy > 0) {
            totalAccuracy += metrics.accuracy;
            accuracyCount++;
          }
        } catch {
          // Skip if metrics not available
        }
      }

      const avgAccuracy = accuracyCount > 0 ? totalAccuracy / accuracyCount : 0;

      setStats({
        totalJobs,
        completedJobs: completedJobs.length,
        avgAccuracy,
        totalRowsCleaned: completedJobs.reduce((sum, job) => sum + (job.progress * 100), 0),
        recentJobs,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getStatusChip = (status: Job['status']) => {
    const config = {
      pending: { color: 'default', icon: <PendingIcon fontSize="small" />, label: 'Pending' },
      running: { color: 'primary', icon: <StartIcon fontSize="small" />, label: 'Running' },
      completed: { color: 'success', icon: <SuccessIcon fontSize="small" />, label: 'Completed' },
      failed: { color: 'error', icon: <ErrorIcon fontSize="small" />, label: 'Failed' },
    };

    const { color, icon, label } = config[status];

    return (
      <Chip
        icon={icon}
        label={label}
        color={color as 'default' | 'primary' | 'success' | 'error'}
        size="small"
        variant="outlined"
      />
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 600 }}>
            Dashboard
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Overview of your data cleaning jobs and performance metrics
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchDashboardData}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            component={Link}
            to="/upload"
            startIcon={<UploadIcon />}
          >
            Upload Dataset
          </Button>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Total Jobs"
            value={stats?.totalJobs || 0}
            subtitle={`${stats?.completedJobs || 0} completed`}
            icon={<JobsIcon />}
            color="primary"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Avg Accuracy"
            value={`${(stats?.avgAccuracy || 0).toFixed(1)}%`}
            subtitle="Across all jobs"
            icon={<TrendingIcon />}
            color="success"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Data Cleaned"
            value={`${((stats?.totalRowsCleaned || 0) / 1000).toFixed(1)}K`}
            subtitle="Rows processed"
            icon={<DataIcon />}
            color="info"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Success Rate"
            value={`${stats?.totalJobs ? ((stats.completedJobs / stats.totalJobs) * 100).toFixed(1) : 0}%`}
            subtitle="Jobs completed"
            icon={<SuccessIcon />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* Recent Jobs Table */}
      <Paper elevation={2}>
        <Box sx={{ p: 3, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Recent Jobs
            </Typography>
            <Button component={Link} to="/jobs" variant="text">
              View All
            </Button>
          </Box>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Job ID</TableCell>
                <TableCell>Dataset</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                // Loading skeletons
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton /></TableCell>
                    <TableCell><Skeleton /></TableCell>
                    <TableCell><Skeleton width={80} /></TableCell>
                    <TableCell><Skeleton width={60} /></TableCell>
                    <TableCell><Skeleton width={100} /></TableCell>
                    <TableCell><Skeleton width={80} /></TableCell>
                  </TableRow>
                ))
              ) : stats?.recentJobs && stats.recentJobs.length > 0 ? (
                stats.recentJobs.map((job) => (
                  <TableRow key={job.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {job.id.slice(0, 8)}...
                      </Typography>
                    </TableCell>
                    <TableCell>{job.datasetName}</TableCell>
                    <TableCell>{getStatusChip(job.status)}</TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {job.progress}%
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="textSecondary">
                        {new Date(job.startedAt).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Button
                        component={Link}
                        to={`/interactive/${job.id}`}
                        size="small"
                        variant="outlined"
                        disabled={job.status === 'pending'}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                      No jobs yet. Start by uploading a dataset!
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Quick Actions */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Quick Actions
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Button
              variant="outlined"
              fullWidth
              component={Link}
              to="/upload"
              startIcon={<UploadIcon />}
              sx={{ py: 2, justifyContent: 'flex-start' }}
            >
              Upload New Dataset
            </Button>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Button
              variant="outlined"
              fullWidth
              component={Link}
              to="/jobs"
              startIcon={<JobsIcon />}
              sx={{ py: 2, justifyContent: 'flex-start' }}
            >
              View All Jobs
            </Button>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Button
              variant="outlined"
              fullWidth
              onClick={fetchDashboardData}
              startIcon={<RefreshIcon />}
              sx={{ py: 2, justifyContent: 'flex-start' }}
            >
              Refresh Dashboard
            </Button>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;
