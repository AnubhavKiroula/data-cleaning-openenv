/**
 * RowViewer component - Display current row data with issue highlighting
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
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CleanIcon,
} from '@mui/icons-material';

interface RowViewerProps {
  rowData: Record<string, unknown>;
  rowIndex: number;
  totalRows: number;
  issues?: string[];
  changedColumns?: Record<string, { before: unknown; after: unknown }>;
}

const RowViewer: React.FC<RowViewerProps> = ({
  rowData,
  rowIndex,
  totalRows,
  issues = [],
  changedColumns = {},
}) => {
  const columns = Object.keys(rowData);
  const progress = totalRows > 0 ? ((rowIndex + 1) / totalRows) * 100 : 0;

  const getValueType = (value: unknown): string => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'float';
    if (typeof value === 'boolean') return 'bool';
    if (typeof value === 'string') return 'string';
    return typeof value;
  };

  const hasIssue = (column: string): boolean => {
    return issues.some((issue) => issue.toLowerCase().includes(column.toLowerCase()));
  };

  const isChanged = (column: string): boolean => {
    return column in changedColumns;
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Row {rowIndex + 1} of {totalRows}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {issues.length > 0 ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <WarningIcon color="warning" fontSize="small" />
                {issues.length} issue{issues.length !== 1 ? 's' : ''} detected
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <CleanIcon color="success" fontSize="small" />
                No issues detected
              </Box>
            )}
          </Typography>
        </Box>
        <Chip
          label={`${Math.round(progress)}% Complete`}
          color={progress === 100 ? 'success' : 'default'}
          variant="outlined"
        />
      </Box>

      {/* Progress Bar */}
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{ mb: 3, height: 8, borderRadius: 4 }}
      />

      {/* Data Table */}
      <TableContainer component={Paper} elevation={1}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: 'grey.100' }}>
              <TableCell sx={{ fontWeight: 600, width: '20%' }}>Column</TableCell>
              <TableCell sx={{ fontWeight: 600, width: '15%' }}>Type</TableCell>
              <TableCell sx={{ fontWeight: 600, width: '35%' }}>Value</TableCell>
              <TableCell sx={{ fontWeight: 600, width: '30%' }}>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {columns.map((column) => {
              const value = rowData[column];
              const issue = hasIssue(column);
              const changed = isChanged(column);
              const changeInfo = changedColumns[column];

              return (
                <TableRow
                  key={column}
                  sx={{
                    bgcolor: issue ? 'error.light' : changed ? 'success.light' : 'transparent',
                    '&:hover': { bgcolor: issue ? 'error.lighter' : changed ? 'success.lighter' : 'grey.50' },
                  }}
                >
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {column}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getValueType(value)}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem' }}
                    />
                  </TableCell>
                  <TableCell>
                    <Box>
                      {changed && changeInfo && (
                        <Typography
                          variant="body2"
                          color="textSecondary"
                          sx={{ textDecoration: 'line-through', fontSize: '0.75rem' }}
                        >
                          {String(changeInfo.before)}
                        </Typography>
                      )}
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: typeof value === 'string' ? 'inherit' : 'monospace',
                          wordBreak: 'break-word',
                        }}
                      >
                        {value === null || value === undefined ? (
                          <Typography component="span" color="error" sx={{ fontStyle: 'italic' }}>
                            null
                          </Typography>
                        ) : (
                          String(value)
                        )}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      {issue && (
                        <Chip
                          icon={<WarningIcon />}
                          label="Issue"
                          color="error"
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {changed && (
                        <Chip
                          icon={<CleanIcon />}
                          label="Modified"
                          color="success"
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {!issue && !changed && (
                        <Chip
                          icon={<CleanIcon />}
                          label="Clean"
                          color="success"
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Legend */}
      <Box sx={{ mt: 2, display: 'flex', gap: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, bgcolor: 'error.light', borderRadius: 1 }} />
          <Typography variant="caption">Has Issue</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, bgcolor: 'success.light', borderRadius: 1 }} />
          <Typography variant="caption">Modified</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, bgcolor: 'transparent', border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }} />
          <Typography variant="caption">Clean</Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default RowViewer;
