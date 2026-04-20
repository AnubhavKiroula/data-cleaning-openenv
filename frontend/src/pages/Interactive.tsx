/**
 * Interactive cleaning page - Row-by-row data cleaning with RL agent suggestions
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  LinearProgress,
  Alert,
  Grid,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Close as CloseIcon,
  Info as InfoIcon,
  Psychology as AgentIcon,
} from '@mui/icons-material';
import RowViewer from '../components/RowViewer';
import AgentSuggestion from '../components/AgentSuggestion';
import ActionPanel from '../components/ActionPanel';
import type { SuggestedAction, CleaningAction } from '../types';
import { getSuggestions, applyAction, skipRow, getJobStatus } from '../services/api';

interface RowData {
  [key: string]: unknown;
}

const MOCK_ROWS: RowData[] = [
  { id: 1, name: 'John Doe', email: 'johndoe@example.com', age: 28, city: 'New York' },
  { id: 2, name: 'Jane Smith', email: 'jane.smith@example.com', age: 34, city: 'Los Angeles' },
  { id: 3, name: 'Bob Johnson', email: 'bob@invalid', age: 45, city: 'Chicago' },
  { id: 4, name: 'Alice Brown', email: 'alice@example.com', age: null, city: 'Houston' },
  { id: 5, name: 'Charlie Wilson', email: 'charlie@example.com', age: 29, city: 'Phoenix' },
];

const MOCK_SUGGESTIONS: SuggestedAction[] = [
  {
    action: 'fix_email',
    column: 'email',
    confidence: 0.92,
    description: 'Fix invalid email format',
    reason: 'Email address appears to be invalid or malformed',
  },
  {
    action: 'fill_missing',
    column: 'age',
    confidence: 0.78,
    description: 'Fill missing value',
    reason: 'Age field is null - can be inferred from similar records',
  },
];

const Interactive: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  
  const [currentRowIndex, setCurrentRowIndex] = useState(0);
  const [totalRows] = useState(MOCK_ROWS.length);
  const [rowData, setRowData] = useState<RowData>(MOCK_ROWS[0]);
  const [issues, setIssues] = useState<string[]>(['email', 'age']);
  const [suggestions, setSuggestions] = useState<SuggestedAction[]>([]);
  const [history, setHistory] = useState<CleaningAction[]>([]);
  const [changedColumns, setChangedColumns] = useState<Record<string, { before: unknown; after: unknown }>>({});
  
  const [loading, setLoading] = useState(true);
  const [fetchingSuggestion, setFetchingSuggestion] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Fetch suggestion for current row
  const fetchSuggestion = useCallback(async () => {
    if (!jobId) return;
    
    try {
      setFetchingSuggestion(true);
      const newSuggestions = await getSuggestions(jobId);
      setSuggestions(newSuggestions);
    } catch (err) {
      // Use mock suggestions if API fails
      setSuggestions(MOCK_SUGGESTIONS);
    } finally {
      setFetchingSuggestion(false);
    }
  }, [jobId]);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      
      // Simulate loading
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      setRowData(MOCK_ROWS[0]);
      setIssues(['email', 'age']);
      await fetchSuggestion();
      
      setLoading(false);
    };

    loadData();
  }, [fetchSuggestion, jobId]);

  const handleAccept = async () => {
    if (!jobId || suggestions.length === 0) return;

    const suggestion = suggestions[0];
    
    try {
      setProcessing(true);
      setError(null);

      await applyAction(jobId, suggestion);

      // Update history
      setHistory((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          type: suggestion.action,
          description: suggestion.description,
          timestamp: new Date().toISOString(),
          confidence: suggestion.confidence,
          before: rowData[suggestion.column],
          after: suggestion.column,
        },
      ]);

      // Mark column as changed
      setChangedColumns((prev) => ({
        ...prev,
        [suggestion.column]: {
          before: rowData[suggestion.column],
          after: 'modified',
        },
      }));

      // Move to next row
      await moveToNextRow();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply action');
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!jobId) return;

    try {
      setProcessing(true);
      setError(null);

      await skipRow(jobId);
      
      // Move to next row
      await moveToNextRow();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip row');
    } finally {
      setProcessing(false);
    }
  };

  const moveToNextRow = async () => {
    if (currentRowIndex < totalRows - 1) {
      const nextIndex = currentRowIndex + 1;
      setCurrentRowIndex(nextIndex);
      setRowData(MOCK_ROWS[nextIndex]);
      setIssues(nextIndex === 2 ? ['email'] : nextIndex === 3 ? ['age'] : []);
      setChangedColumns({});
      await fetchSuggestion();
    } else {
      // All rows processed
      setSuggestions([]);
    }
  };

  const handlePrev = async () => {
    if (currentRowIndex > 0) {
      const prevIndex = currentRowIndex - 1;
      setCurrentRowIndex(prevIndex);
      setRowData(MOCK_ROWS[prevIndex]);
      setIssues(prevIndex === 2 ? ['email'] : prevIndex === 3 ? ['age'] : []);
      setChangedColumns({});
      await fetchSuggestion();
    }
  };

  const handleNext = async () => {
    await moveToNextRow();
  };

  const currentSuggestion = suggestions[0];

  if (loading) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          Interactive Cleaning
        </Typography>
        <LinearProgress sx={{ mt: 2 }} />
        <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
          Loading session...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          Interactive Cleaning
        </Typography>
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
        <Button variant="outlined" onClick={() => navigate('/jobs')} sx={{ mt: 2 }}>
          Back to Jobs
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 600 }}>
            Interactive Cleaning
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Job ID: {jobId}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Help">
            <IconButton onClick={() => setShowHelp(true)}>
              <InfoIcon />
            </IconButton>
          </Tooltip>
          <Button variant="outlined" onClick={() => navigate('/jobs')} startIcon={<CloseIcon />}>
            Exit
          </Button>
        </Box>
      </Box>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Row Viewer */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <RowViewer
              rowData={rowData}
              rowIndex={currentRowIndex}
              totalRows={totalRows}
              issues={issues}
              changedColumns={changedColumns}
            />
          </Paper>
        </Grid>

        {/* Agent Suggestion & Actions */}
        <Grid size={{ xs: 12, md: 6 }}>
          {fetchingSuggestion ? (
            <Paper elevation={2} sx={{ p: 3, textAlign: 'center' }}>
              <LinearProgress sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary">
                <AgentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Getting agent suggestion...
              </Typography>
            </Paper>
          ) : currentSuggestion ? (
            <>
              <AgentSuggestion
                action={currentSuggestion.action}
                column={currentSuggestion.column}
                proposedValue="modified_value"
                agentName="DQN Agent"
                confidence={currentSuggestion.confidence}
                explanation={currentSuggestion.reason}
              />
              
              <Box sx={{ mt: 3 }}>
                <ActionPanel
                  onAccept={handleAccept}
                  onReject={handleReject}
                  onPrev={handlePrev}
                  onNext={handleNext}
                  canGoBack={currentRowIndex > 0}
                  canGoForward={currentRowIndex < totalRows - 1}
                  isProcessing={processing}
                  hasSuggestion={suggestions.length > 0}
                />
              </Box>
            </>
          ) : (
            <Paper elevation={2} sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                {currentRowIndex >= totalRows - 1 ? 'All Rows Processed!' : 'No Suggestions'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {currentRowIndex >= totalRows - 1
                  ? 'You have reviewed all rows in this dataset.'
                  : 'No cleaning suggestions for this row.'}
              </Typography>
              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  onClick={() => navigate('/jobs')}
                >
                  Go to Jobs
                </Button>
              </Box>
            </Paper>
          )}
        </Grid>
      </Grid>

      {/* Action History */}
      {history.length > 0 && (
        <Paper elevation={2} sx={{ mt: 3, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Action History ({history.length} actions)
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {history.slice(-5).map((action, index) => (
              <Typography key={index} variant="body2" sx={{ px: 1, py: 0.5, bgcolor: 'success.light', borderRadius: 1 }}>
                {action.description}
              </Typography>
            ))}
          </Box>
        </Paper>
      )}

      {/* Help Dialog */}
      <Dialog open={showHelp} onClose={() => setShowHelp(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Interactive Cleaning Help</DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 1.5 }}>
            <strong>Accept (Enter):</strong> Apply the suggested cleaning action to the current row.
          </Typography>
          <Typography variant="body1" sx={{ mb: 1.5 }}>
            <strong>Reject (Esc):</strong> Discard the suggestion and move to the next row.
          </Typography>
          <Typography variant="body1" sx={{ mb: 1.5 }}>
            <strong>Previous/Next:</strong> Navigate between rows manually.
          </Typography>
          <Typography variant="body2" color="textSecondary">
            The confidence score (0-100%) indicates how certain the RL agent is about each suggestion.
            Green = High confidence (80%+), Yellow = Medium (50-80%), Red = Low (&lt;50%)
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHelp(false)}>Got it</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Interactive;
