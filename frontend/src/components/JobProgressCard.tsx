/**
 * JobProgressCard component - Display job status and progress
 */

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  LinearProgress,
  Chip,
} from '@mui/material';
import {
  AccessTime as TimeIcon,
  Speed as SpeedIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
} from '@mui/icons-material';

interface JobProgressCardProps {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'running' | 'queued';
  rowsProcessed: number;
  totalRows: number;
  startedAt?: string;
  completedAt?: string;
  accuracy?: number;
}

const JobProgressCard: React.FC<JobProgressCardProps> = ({
  jobId,
  status,
  rowsProcessed,
  totalRows,
  startedAt,
  completedAt,
  accuracy,
}) => {
  const progress = totalRows > 0 ? (rowsProcessed / totalRows) * 100 : 0;

  const getStatusColor = (): 'default' | 'primary' | 'success' | 'error' | 'warning' => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'processing':
      case 'running':
        return 'primary';
      case 'queued':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CompleteIcon />;
      case 'failed':
        return <ErrorIcon />;
      case 'processing':
      case 'running':
        return <PendingIcon />;
      default:
        return <PendingIcon />;
    }
  };

  const getStatusLabel = (): string => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'processing':
      case 'running':
        return 'Processing';
      case 'queued':
        return 'Queued';
      default:
        return 'Pending';
    }
  };

  const formatElapsedTime = (): string => {
    if (!startedAt) return 'N/A';
    const start = new Date(startedAt);
    const end = completedAt ? new Date(completedAt) : new Date();
    const diffMs = end.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffHours > 0) {
      return `${diffHours}h ${diffMins % 60}m`;
    }
    return `${diffMins}m`;
  };

  const estimateRemaining = (): string => {
    if ((status !== 'processing' && status !== 'running') || !startedAt || rowsProcessed === 0) return 'Calculating...';
    
    const start = new Date(startedAt);
    const now = new Date();
    const elapsedMs = now.getTime() - start.getTime();
    const rate = rowsProcessed / elapsedMs;
    const remaining = totalRows - rowsProcessed;
    const remainingMs = remaining / rate;
    const remainingMins = Math.ceil(remainingMs / 60000);

    if (remainingMins > 60) {
      const hours = Math.floor(remainingMins / 60);
      return `~${hours}h ${remainingMins % 60}m`;
    }
    return `~${remainingMins}m`;
  };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
        <Box>
          <Typography variant="subtitle2" color="textSecondary">
            Job ID
          </Typography>
          <Typography variant="body1" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
            {jobId}
          </Typography>
        </Box>
        <Chip
          icon={getStatusIcon() as React.ReactElement}
          label={getStatusLabel()}
          color={getStatusColor()}
          size="small"
        />
      </Box>

      {/* Progress */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="textSecondary">
            Progress
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {rowsProcessed.toLocaleString()} / {totalRows.toLocaleString()} rows ({progress.toFixed(1)}%)
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          color={status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'primary'}
          sx={{ height: 10, borderRadius: 5 }}
        />
      </Box>

      {/* Stats */}
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TimeIcon fontSize="small" color="action" />
          <Box>
            <Typography variant="caption" color="textSecondary">
              Elapsed Time
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {formatElapsedTime()}
            </Typography>
          </Box>
        </Box>

        {status === 'processing' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SpeedIcon fontSize="small" color="action" />
            <Box>
              <Typography variant="caption" color="textSecondary">
                Est. Remaining
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {estimateRemaining()}
              </Typography>
            </Box>
          </Box>
        )}

        {accuracy !== undefined && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CompleteIcon fontSize="small" color="success" />
            <Box>
              <Typography variant="caption" color="textSecondary">
                Accuracy
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {(accuracy * 100).toFixed(1)}%
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default JobProgressCard;
