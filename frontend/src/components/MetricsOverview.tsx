/**
 * MetricsOverview component - Display aggregated metrics in stat cards
 */

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
} from '@mui/material';
import {
  Work as JobsIcon,
  Speed as AccuracyIcon,
  TableRows as RowsIcon,
  Storage as DataIcon,
} from '@mui/icons-material';

interface MetricsOverviewProps {
  totalJobs: number;
  avgAccuracy: number;
  totalRowsCleaned: number;
  totalDataProcessed: number;
}

const MetricsOverview: React.FC<MetricsOverviewProps> = ({
  totalJobs,
  avgAccuracy,
  totalRowsCleaned,
  totalDataProcessed,
}) => {
  const formatDataSize = (bytes: number): string => {
    if (bytes >= 1073741824) {
      return `${(bytes / 1073741824).toFixed(1)} GB`;
    }
    if (bytes >= 1048576) {
      return `${(bytes / 1048576).toFixed(1)} MB`;
    }
    if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${bytes} B`;
  };

  const statCards = [
    {
      icon: <JobsIcon fontSize="large" />,
      label: 'Total Jobs',
      value: totalJobs.toLocaleString(),
      color: '#1976d2',
    },
    {
      icon: <AccuracyIcon fontSize="large" />,
      label: 'Avg Accuracy',
      value: `${(avgAccuracy * 100).toFixed(1)}%`,
      color: '#2e7d32',
    },
    {
      icon: <RowsIcon fontSize="large" />,
      label: 'Total Rows Cleaned',
      value: totalRowsCleaned.toLocaleString(),
      color: '#ed6c02',
    },
    {
      icon: <DataIcon fontSize="large" />,
      label: 'Total Data Processed',
      value: formatDataSize(totalDataProcessed),
      color: '#9c27b0',
    },
  ];

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
        Metrics Overview
      </Typography>
      <Grid container spacing={2}>
        {statCards.map((card, index) => (
          <Grid size={{ xs: 6, md: 3 }} key={index}>
            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                bgcolor: `${card.color}10`,
                border: '1px solid',
                borderColor: `${card.color}30`,
                textAlign: 'center',
                height: '100%',
              }}
            >
              <Box sx={{ color: card.color, mb: 1 }}>
                {card.icon}
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: card.color }}>
                {card.value}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {card.label}
              </Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
    </Paper>
  );
};

export default MetricsOverview;
