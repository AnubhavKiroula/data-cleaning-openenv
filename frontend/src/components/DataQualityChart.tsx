/**
 * DataQualityChart component - Before/after comparison bar chart
 */

import React from 'react';
import {
  Box,
  Typography,
  Paper,
} from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface DataQualityChartProps {
  beforeCleaning: {
    missingValues: number;
    duplicates: number;
    outliers: number;
    qualityScore: number;
  };
  afterCleaning: {
    missingValues: number;
    duplicates: number;
    outliers: number;
    qualityScore: number;
  };
  title?: string;
}

const DataQualityChart: React.FC<DataQualityChartProps> = ({
  beforeCleaning,
  afterCleaning,
  title = 'Data Quality Comparison',
}) => {
  const labels = ['Missing Values (%)', 'Duplicates', 'Outliers', 'Quality Score'];

  const data = {
    labels,
    datasets: [
      {
        label: 'Before Cleaning',
        data: [
          beforeCleaning.missingValues,
          beforeCleaning.duplicates,
          beforeCleaning.outliers,
          beforeCleaning.qualityScore * 100,
        ],
        backgroundColor: 'rgba(54, 162, 235, 0.7)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
      {
        label: 'After Cleaning',
        data: [
          afterCleaning.missingValues,
          afterCleaning.duplicates,
          afterCleaning.outliers,
          afterCleaning.qualityScore * 100,
        ],
        backgroundColor: 'rgba(75, 192, 192, 0.7)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Box sx={{ height: 300 }}>
        <Bar data={data} options={options} />
      </Box>
    </Paper>
  );
};

export default DataQualityChart;
