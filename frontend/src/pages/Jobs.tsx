/**
 * Jobs page - Job history and management
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  IconButton,
  Pagination,
  Skeleton,
  Alert,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  HourglassEmpty as RunningIcon,
  PlayArrow as StartIcon,
} from '@mui/icons-material';
import type { Job } from '../types';
import { getJobs } from '../services/api';

const Jobs: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchJobs = async () => {
    try {
      setLoading(true);
      setError(null);

      try {
        const response = await getJobs(page, 20);
        setJobs(response.items);
        setTotalPages(Math.ceil(response.total / response.pageSize));
      } catch (err) {
        // Fallback: show empty list if API fails
        console.warn('Failed to fetch jobs, showing empty list:', err);
        setJobs([]);
        setTotalPages(1);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const getStatusChip = (status: Job['status']) => {
    const config = {
      pending: { 
        color: 'default' as const, 
        icon: <PendingIcon fontSize="small" />, 
        label: 'Pending' 
      },
      running: { 
        color: 'primary' as const, 
        icon: <RunningIcon fontSize="small" />, 
        label: 'Running' 
      },
      processing: { 
        color: 'primary' as const, 
        icon: <StartIcon fontSize="small" />, 
        label: 'Processing' 
      },
      queued: { 
        color: 'info' as const, 
        icon: <PendingIcon fontSize="small" />, 
        label: 'Queued' 
      },
      completed: { 
        color: 'success' as const, 
        icon: <SuccessIcon fontSize="small" />, 
        label: 'Completed' 
      },
      failed: { 
        color: 'error' as const, 
        icon: <ErrorIcon fontSize="small" />, 
        label: 'Failed' 
      },
    };

    const cfg = config[status] || config['pending'];
    const { color, icon, label } = cfg;

    return (
      <Chip
        icon={icon}
        label={label}
        color={color}
        size="small"
        variant="outlined"
      />
    );
  };

  const filteredJobs = jobs.filter((job) => {
    if (statusFilter !== 'all' && job.status !== statusFilter) {
      return false;
    }
    if (searchQuery && !(job.datasetName || job.dataset_name || '').toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 600 }}>
        Job History
      </Typography>
      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        View and manage all your data cleaning jobs
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField
            placeholder="Search by dataset name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
            sx={{ minWidth: 250 }}
          />
          
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All Status</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchJobs}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
      </Paper>

      {/* Jobs Table */}
      <TableContainer component={Paper} elevation={2}>
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
            ) : filteredJobs.length > 0 ? (
              filteredJobs.map((job) => (
                <TableRow key={job.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {job.id.slice(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>{job.datasetName}</TableCell>
                  <TableCell>{getStatusChip(job.status)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2">{job.progress ?? 0}%</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="textSecondary">
                      {new Date(job.startedAt || job.created_at || Date.now()).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Tooltip title="View Details">
                        <IconButton
                          component={Link}
                          to={`/interactive/${job.id}`}
                          size="small"
                          color="primary"
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                    No jobs found matching your filters
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, value) => setPage(value)}
            color="primary"
          />
        </Box>
      )}

      {/* Summary Stats */}
      <Paper elevation={1} sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Summary
        </Typography>
        <Box sx={{ display: 'flex', gap: 4 }}>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Total Jobs
            </Typography>
            <Typography variant="h6">
              {jobs.length}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Completed
            </Typography>
            <Typography variant="h6" color="success.main">
              {jobs.filter((j) => j.status === 'completed').length}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Running
            </Typography>
            <Typography variant="h6" color="primary.main">
              {jobs.filter((j) => j.status === 'running').length}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Failed
            </Typography>
            <Typography variant="h6" color="error.main">
              {jobs.filter((j) => j.status === 'failed').length}
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default Jobs;
