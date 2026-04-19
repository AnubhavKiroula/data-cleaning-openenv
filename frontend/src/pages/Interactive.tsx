/**
 * Interactive cleaning page - Real-time data cleaning with AI suggestions
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Stepper,
  Step,
  StepLabel,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  CheckCircle as AcceptIcon,
  Cancel as RejectIcon,
  SkipNext as SkipIcon,
  Undo as UndoIcon,
  NavigateNext as NextIcon,
  NavigateBefore as PrevIcon,
  Close as CloseIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import type { InteractiveSession, SuggestedAction, CleaningAction } from '../types';
import { startInteractiveSession, getSuggestions, applyAction, skipRow } from '../services/api';

const Interactive: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<InteractiveSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    const loadSession = async () => {
      if (!jobId) return;

      try {
        setLoading(true);
        const newSession = await startInteractiveSession(jobId);
        setSession(newSession);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session');
      } finally {
        setLoading(false);
      }
    };

    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const handleAccept = async (action: SuggestedAction) => {
    if (!jobId || !session) return;

    try {
      setProcessing(true);
      await applyAction(jobId, action);
      
      // Refresh suggestions
      const suggestions = await getSuggestions(jobId);
      setSession({
        ...session,
        suggestions,
        history: [
          ...session.history,
          {
            id: Date.now().toString(),
            timestamp: new Date().toISOString(),
            type: action.action,
            description: action.description,
            confidence: action.confidence,
            before: null,
            after: null,
          } as CleaningAction,
        ],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply action');
    } finally {
      setProcessing(false);
    }
  };

  const handleSkip = async () => {
    if (!jobId || !session) return;

    try {
      setProcessing(true);
      await skipRow(jobId);
      
      // Refresh suggestions
      const suggestions = await getSuggestions(jobId);
      setSession({
        ...session,
        suggestions,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip row');
    } finally {
      setProcessing(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.5) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
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
        <Typography variant="h4" gutterBottom>
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
        <Typography variant="h4" component="h1" sx={{ fontWeight: 600 }}>
          Interactive Cleaning
        </Typography>
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

      {/* Progress Stepper */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Stepper activeStep={0} alternativeLabel>
          <Step completed={false}>
            <StepLabel>Review Suggestions</StepLabel>
          </Step>
          <Step>
            <StepLabel>Apply Changes</StepLabel>
          </Step>
          <Step>
            <StepLabel>Export Cleaned Data</StepLabel>
          </Step>
        </Stepper>
      </Paper>

      {session && (
        <>
          {/* Current Data Preview */}
          <Card elevation={2} sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Current Row Data
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Field</TableCell>
                      <TableCell>Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(session.currentRow).map(([key, value]) => (
                      <TableRow key={key}>
                        <TableCell sx={{ fontWeight: 500 }}>{key}</TableCell>
                        <TableCell>{String(value)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* AI Suggestions */}
          <Typography variant="h6" gutterBottom>
            Suggested Actions
          </Typography>

          {session.suggestions.length > 0 ? (
            session.suggestions.map((suggestion, index) => (
              <Card key={index} elevation={2} sx={{ mb: 2, borderLeft: 4, borderColor: `${getConfidenceColor(suggestion.confidence)}.main` }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" component="div">
                        {suggestion.description}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {suggestion.reason}
                      </Typography>
                    </Box>
                    <Chip
                      label={`${(suggestion.confidence * 100).toFixed(0)}% confidence`}
                      color={getConfidenceColor(suggestion.confidence)}
                      size="small"
                    />
                  </Box>

                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Action:</strong> {suggestion.action}
                  </Typography>
                </CardContent>
                <CardActions sx={{ justifyContent: 'flex-end', gap: 1 }}>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<RejectIcon />}
                    disabled={processing}
                  >
                    Reject
                  </Button>
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={<AcceptIcon />}
                    onClick={() => handleAccept(suggestion)}
                    disabled={processing}
                  >
                    Accept
                  </Button>
                </CardActions>
              </Card>
            ))
          ) : (
            <Alert severity="info" sx={{ mb: 3 }}>
              No suggestions available for this row. It looks clean!
            </Alert>
          )}

          {/* Navigation Actions */}
          <Paper elevation={2} sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Button
              variant="outlined"
              startIcon={<PrevIcon />}
              disabled={processing}
            >
              Previous
            </Button>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                startIcon={<SkipIcon />}
                onClick={handleSkip}
                disabled={processing}
              >
                Skip Row
              </Button>
              <Button
                variant="outlined"
                startIcon={<UndoIcon />}
                disabled={processing || session.history.length === 0}
              >
                Undo
              </Button>
            </Box>

            <Button
              variant="contained"
              endIcon={<NextIcon />}
              disabled={processing}
            >
              Next
            </Button>
          </Paper>

          {/* Action History */}
          {session.history.length > 0 && (
            <Card elevation={2} sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Action History ({session.history.length})
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Action</TableCell>
                        <TableCell>Time</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {session.history.slice(-5).map((action) => (
                        <TableRow key={action.id}>
                          <TableCell>{action.description}</TableCell>
                          <TableCell>
                            {new Date(action.timestamp).toLocaleTimeString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Help Dialog */}
      <Dialog open={showHelp} onClose={() => setShowHelp(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Interactive Cleaning Help</DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ marginBottom: 1 }}>
            <strong>Accept:</strong> Apply the suggested cleaning action to the current row.
          </Typography>
          <Typography variant="body1" sx={{ marginBottom: 1 }}>
            <strong>Reject:</strong> Discard the suggestion and keep the original data.
          </Typography>
          <Typography variant="body1" sx={{ marginBottom: 1 }}>
            <strong>Skip:</strong> Move to the next row without making any changes.
          </Typography>
          <Typography variant="body1" sx={{ marginBottom: 1 }}>
            <strong>Undo:</strong> Revert the last action you took.
          </Typography>
          <Typography variant="body2" color="textSecondary">
            The confidence score indicates how certain the AI is about each suggestion.
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
