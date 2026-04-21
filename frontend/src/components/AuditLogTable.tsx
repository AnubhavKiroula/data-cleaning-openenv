/**
 * AuditLogTable component - Display detailed audit log with pagination
 */

import React, { useState } from 'react';
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
  TextField,
  InputAdornment,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
} from '@mui/icons-material';

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

interface AuditLogTableProps {
  entries: AuditLogEntry[];
  loading?: boolean;
}

const AuditLogTable: React.FC<AuditLogTableProps> = ({ entries, loading = false }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [searchTerm, setSearchTerm] = useState('');

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const filteredEntries = entries.filter((entry) => {
    const searchLower = searchTerm.toLowerCase();
    return (
      entry.column.toLowerCase().includes(searchLower) ||
      entry.actionType.toLowerCase().includes(searchLower) ||
      entry.agent.toLowerCase().includes(searchLower)
    );
  });

  const paginatedEntries = filteredEntries.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const getConfidenceColor = (confidence: number): 'success' | 'warning' | 'error' => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.5) return 'warning';
    return 'error';
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const formatValue = (value: string): string => {
    if (!value || value === 'null' || value === '') {
      return '-';
    }
    return value.length > 50 ? `${value.substring(0, 50)}...` : value;
  };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Audit Log
        </Typography>
        <TextField
          size="small"
          placeholder="Search by column, action, or agent..."
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
          sx={{ width: 300 }}
        />
      </Box>

      {loading ? (
        <LinearProgress />
      ) : (
        <>
          <TableContainer>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Row #</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Column</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Old Value</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>New Value</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Action Type</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Agent</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Confidence</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Timestamp</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedEntries.length > 0 ? (
                  paginatedEntries.map((entry, index) => (
                    <TableRow key={index} hover>
                      <TableCell>{entry.rowNumber}</TableCell>
                      <TableCell>
                        <Chip label={entry.column} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                        {formatValue(entry.oldValue)}
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                        {formatValue(entry.newValue)}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={entry.actionType.replace(/_/g, ' ')}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{entry.agent}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={entry.confidence * 100}
                            color={getConfidenceColor(entry.confidence)}
                            sx={{ width: 50, height: 6, borderRadius: 3 }}
                          />
                          <Typography variant="caption">
                            {(entry.confidence * 100).toFixed(0)}%
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="textSecondary">
                          {formatTimestamp(entry.timestamp)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      <Typography variant="body2" color="textSecondary" sx={{ py: 3 }}>
                        No audit log entries found
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={filteredEntries.length}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[25, 50, 100]}
          />
        </>
      )}
    </Paper>
  );
};

export default AuditLogTable;
