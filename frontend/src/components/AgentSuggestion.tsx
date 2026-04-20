/**
 * AgentSuggestion component - Display RL agent recommendation with confidence
 */

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  LinearProgress,
  Chip,
  Divider,
} from '@mui/material';
import {
  AutoFixHigh as AgentIcon,
  Psychology as BrainIcon,
  Lightbulb as IdeaIcon,
} from '@mui/icons-material';

interface AgentSuggestionProps {
  action: string;
  column: string;
  proposedValue: unknown;
  agentName: string;
  confidence: number;
  explanation: string;
}

const AgentSuggestion: React.FC<AgentSuggestionProps> = ({
  action,
  column,
  proposedValue,
  agentName,
  confidence,
  explanation,
}) => {
  const getConfidenceColor = (): 'success' | 'warning' | 'error' => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.5) return 'warning';
    return 'error';
  };

  const getConfidenceLabel = (): string => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  };

  const getActionLabel = (actionType: string): string => {
    const labels: Record<string, string> = {
      fill_missing: 'Fill Missing Value',
      remove_duplicate: 'Remove Duplicate',
      fix_outlier: 'Fix Outlier',
      standardize: 'Standardize Format',
      correct_typo: 'Correct Typo',
      remove_whitespace: 'Remove Whitespace',
      convert_type: 'Convert Type',
      drop_row: 'Drop Row',
      no_action: 'No Action Needed',
    };
    return labels[actionType] || actionType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const confidenceColor = getConfidenceColor();
  const confidencePercent = Math.round(confidence * 100);

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <AgentIcon color="primary" />
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Agent Suggestion
        </Typography>
        <Chip
          icon={<BrainIcon />}
          label={agentName}
          color="primary"
          size="small"
          variant="outlined"
        />
      </Box>

      {/* Action */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 0.5 }}>
          Recommended Action
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={getActionLabel(action)}
            color={confidenceColor}
            variant="filled"
          />
          <Typography variant="body2" color="textSecondary">
            on column <strong>{column}</strong>
          </Typography>
        </Box>
      </Box>

      {/* Proposed Value */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 0.5 }}>
          Proposed Value
        </Typography>
        <Paper
          variant="outlined"
          sx={{
            p: 1.5,
            bgcolor: 'grey.50',
            fontFamily: 'monospace',
            fontSize: '0.875rem',
          }}
        >
          {proposedValue === null || proposedValue === undefined ? (
            <Typography color="error" sx={{ fontStyle: 'italic' }}>null</Typography>
          ) : (
            String(proposedValue)
          )}
        </Paper>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Confidence Score */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IdeaIcon color={confidenceColor} fontSize="small" />
            <Typography variant="body2" color="textSecondary">
              Confidence Score
            </Typography>
          </Box>
          <Chip
            label={`${confidencePercent}% - ${getConfidenceLabel()}`}
            color={confidenceColor}
            size="small"
          />
        </Box>
        <LinearProgress
          variant="determinate"
          value={confidencePercent}
          color={confidenceColor}
          sx={{ height: 8, borderRadius: 4 }}
        />
      </Box>

      {/* Explanation */}
      <Box>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 0.5 }}>
          Explanation
        </Typography>
        <Typography variant="body2">
          {explanation}
        </Typography>
      </Box>
    </Paper>
  );
};

export default AgentSuggestion;
