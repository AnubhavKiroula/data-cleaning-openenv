/**
 * JobHistory page - Display job history with filters and table
 */

import React, { useState, useEffect } from 'react';
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
  TablePagination,
  Chip,
  TextField,
  MenuItem,
  InputAdornment,
  Button,
  Grid,
  LinearProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import JobProgressCard from '../components/JobProgressCard';
import AuditLogTable from '../components/AuditLogTable';
import DataQualityChart from '../components/DataQualityChart';
import { getJobs } from '../services/api';
import type { Job } from '../types';

type StatusFilter = 'all' | 'completed' | 'failed' | 'processing';

interface AuditLogEntry {
  rowNumber: number;
  column: string;
  oldValue: string;
  newValue: string;
  actionType: string;
  agent: string;
  confidence: number;
  timestamp: string;
}

const JobHistory: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const fetchJobs = async () => {
      setLoading(true);
      try {
        const response = await getJobs(1, 100);
        setJobs(response.items);
      } catch {
        // Use mock data for demo
        setJobs([
          {
            id: 'job-001',
            datasetId: 'ds-001',
            datasetName: 'dataset-1.csv',
            status: 'completed',
            progress: 100,
            startedAt: '2024-01-15T10:00:00Z',
            completedAt: '2024-01-15T10:30:00Z',
            actions: [],
          },
          {
            id: 'job-002',
            datasetId: 'ds-002',
            datasetName: 'dataset-2.csv',
            status: 'running',
            progress: 50,
            startedAt: '2024-01-15T11:00:00Z',
            actions: [],
          },
          {
            id: 'job-003',
            datasetId: 'ds-003',
            datasetName: 'dataset-3.csv',
            status: 'failed',
            progress: 20,
            startedAt: '2024-01-15T09:00:00Z',
            error: 'Connection timeout',
            actions: [],
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter((job) => {
    const matchesStatus = statusFilter === 'all' || job.status === statusFilter;
    const matchesSearch = job.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const sortedJobs = [...filteredJobs].sort(
    (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
  );

  const paginatedJobs = sortedJobs.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleRowClick = async (job: Job) => {
    setSelectedJob(job);
    setShowDetails(true);
    
    // Mock audit log data
    setAuditLog([
      {
        rowNumber: 1,
        column: 'email',
        oldValue: 'invalid@email',
        newValue: 'invalid@email.com',
        actionType: 'fix_email',
        agent: 'DQN Agent',
        confidence: 0.92,
        timestamp: '2024-01-15T10:25:00Z',
      },
      {
        rowNumber: 2,
        column: 'age',
        oldValue: 'null',
        newValue: '28',
        actionType: 'fill_missing',
        agent: 'DQN Agent',
        confidence: 0.78,
        timestamp: '2024-01-15T10:24:00Z',
      },
      {
        rowNumber: 3,
        column: 'name',
        oldValue: 'john doe',
        newValue: 'John Doe',
        actionType: 'standardize',
        agent: 'DQN Agent',
        confidence: 0.95,
        timestamp: '2024-01-15T10:23:00Z',
      },
    ]);
  };

  const getStatusColor = (status: string): 'success' | 'error' | 'primary' | 'default' => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'processing':
        return 'primary';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 600 }}>
        Job History
      </Typography>
      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        View and manage your data cleaning jobs
      </Typography>

      {/* Filters */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search by Job ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField
              fullWidth
              select
              size="small"
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <FilterIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="processing">Processing</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, md: 5 }}>
            <Typography variant="body2" color="textSecondary">
              Showing {paginatedJobs.length} of {filteredJobs.length} jobs
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Jobs Table */}
      <Paper elevation={2} sx={{ mb: 3 }}>
        {loading ? (
          <LinearProgress />
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: 'grey.100' }}>
                  <TableCell sx={{ fontWeight: 600 }}>Job ID</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Task Type</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Progress</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Accuracy</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Started</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Completed</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedJobs.map((job) => (
                  <TableRow
                    key={job.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleRowClick(job)}
                  >
                    <TableCell sx={{ fontFamily: 'monospace' }}>{job.id}</TableCell>
                    <TableCell>
                      <Chip
                        label={job.status}
                        color={getStatusColor(job.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={job.datasetName}
                        variant="outlined"
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
                        <LinearProgress
                          variant="determinate"
                          value={job.progress}
                          sx={{ flex: 1, height: 6 }}
                        />
                        <Typography variant="caption">
                          {job.progress}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      -
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatDate(job.startedAt)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {job.completedAt ? formatDate(job.completedAt) : '-'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        <TablePagination
          component="div"
          count={filteredJobs.length}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25]}
        />
      </Paper>

      {/* Job Details Modal */}
      {showDetails && selectedJob && (
        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              Job Details: {selectedJob.id}
            </Typography>
            <Button variant="outlined" onClick={() => setShowDetails(false)}>
              Close
            </Button>
          </Box>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <JobProgressCard
                jobId={selectedJob.id}
                status={selectedJob.status as 'pending' | 'processing' | 'completed' | 'failed'}
                rowsProcessed={Math.round(selectedJob.progress * 10)}
                totalRows={1000}
                startedAt={selectedJob.startedAt}
                completedAt={selectedJob.completedAt}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <DataQualityChart
                beforeCleaning={{
                  missingValues: 15,
                  duplicates: 50,
                  outliers: 25,
                  qualityScore: 0.65,
                }}
                afterCleaning={{
                  missingValues: 2,
                  duplicates: 5,
                  outliers: 3,
                  qualityScore: 0.95,
                }}
              />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <AuditLogTable entries={auditLog} />
            </Grid>
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default JobHistory;
