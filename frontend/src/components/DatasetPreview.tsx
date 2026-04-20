/**
 * DatasetPreview component - Display dataset metadata and data table
 */

import React from 'react';
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
  LinearProgress,
  Grid,
  Button,
} from '@mui/material';
import {
  Description as FileIcon,
  TableChart as TableIcon,
  Speed as ScoreIcon,
  CalendarToday as DateIcon,
  PlayArrow as PlayIcon,
} from '@mui/icons-material';
import type { Dataset, UploadResponse } from '../types';

interface DatasetPreviewProps {
  dataset: Dataset | UploadResponse | null;
  previewData?: Record<string, unknown>[];
  loading?: boolean;
  onStartCleaning?: () => void;
}

const DatasetPreview: React.FC<DatasetPreviewProps> = ({
  dataset,
  previewData,
  loading = false,
  onStartCleaning,
}) => {
  if (!dataset) {
    return null;
  }

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString();
  };

  const getScoreColor = (score: number): 'success' | 'warning' | 'error' => {
    if (score >= 80) return 'success';
    if (score >= 50) return 'warning';
    return 'error';
  };

  const getColumnNames = (): string[] => {
    if ('columns' in dataset && Array.isArray(dataset.columns)) {
      return dataset.columns;
    }
    if (previewData && previewData.length > 0) {
      return Object.keys(previewData[0]);
    }
    return [];
  };

  const getQualityScore = (): number => {
    if ('data_quality_score' in dataset) {
      return Math.round((dataset as any).data_quality_score * 100);
    }
    if ('score' in dataset) {
      return (dataset as any).score;
    }
    return 0;
  };

  const columns = getColumnNames();
  const qualityScore = getQualityScore();

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
        Dataset Preview
      </Typography>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Metadata Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <FileIcon color="primary" fontSize="small" />
              <Typography variant="body2" color="textSecondary">
                File Name
              </Typography>
            </Box>
            <Typography variant="body1" sx={{ fontWeight: 500 }} noWrap>
              {dataset.filename}
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <TableIcon color="primary" fontSize="small" />
              <Typography variant="body2" color="textSecondary">
                Dimensions
              </Typography>
            </Box>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {dataset.rows.toLocaleString()} rows × {columns.length} cols
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <ScoreIcon color="primary" fontSize="small" />
              <Typography variant="body2" color="textSecondary">
                Quality Score
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {qualityScore}%
              </Typography>
              <Chip
                label={qualityScore >= 80 ? 'Good' : qualityScore >= 50 ? 'Fair' : 'Poor'}
                color={getScoreColor(qualityScore)}
                size="small"
              />
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <DateIcon color="primary" fontSize="small" />
              <Typography variant="body2" color="textSecondary">
                Uploaded
              </Typography>
            </Box>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {'uploadedAt' in dataset ? formatDate(dataset.uploadedAt) : 'Just now'}
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Data Quality Progress */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Data Quality
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ flex: 1 }}>
            <LinearProgress
              variant="determinate"
              value={qualityScore}
              color={getScoreColor(qualityScore)}
              sx={{ height: 10, borderRadius: 5 }}
            />
          </Box>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {qualityScore}% Clean
          </Typography>
        </Box>
        <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
          {100 - qualityScore}% issues detected that need cleaning
        </Typography>
      </Paper>

      {/* Column Names */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Columns ({columns.length})
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {columns.map((col) => (
            <Chip key={col} label={col} variant="outlined" size="small" />
          ))}
        </Box>
      </Paper>

      {/* Data Preview Table */}
      {previewData && previewData.length > 0 && (
        <Paper elevation={1}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2">
              Preview (First {Math.min(previewData.length, 5)} rows)
            </Typography>
          </Box>
          <TableContainer sx={{ maxHeight: 300 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {columns.map((col) => (
                    <TableCell key={col} sx={{ fontWeight: 600 }}>
                      {col}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {previewData.slice(0, 5).map((row, rowIndex) => (
                  <TableRow key={rowIndex} hover>
                    {columns.map((col) => (
                      <TableCell key={col} sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {row[col] !== undefined && row[col] !== null
                          ? String(row[col])
                          : <Typography color="textSecondary" sx={{ fontStyle: 'italic' }}>null</Typography>}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Empty State */}
      {!previewData && (
        <Paper elevation={1} sx={{ p: 4, textAlign: 'center' }}>
          <TableIcon sx={{ fontSize: 48, color: 'textSecondary', mb: 1 }} />
          <Typography variant="body1" color="textSecondary">
            No preview data available
          </Typography>
        </Paper>
      )}

      {/* Start Cleaning Button */}
      {onStartCleaning && (
        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<PlayIcon />}
            onClick={onStartCleaning}
            size="large"
          >
            Start Cleaning
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default DatasetPreview;
