/**
 * ActionPanel component - Accept/reject/navigate buttons with keyboard shortcuts
 */

import React, { useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Typography,
  Paper,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Check as AcceptIcon,
  Close as RejectIcon,
  Edit as EditIcon,
  NavigateBefore as PrevIcon,
  NavigateNext as NextIcon,
  Keyboard as KeyboardIcon,
} from '@mui/icons-material';

interface ActionPanelProps {
  onAccept: () => void;
  onReject: () => void;
  onEdit?: () => void;
  onPrev: () => void;
  onNext: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  isProcessing?: boolean;
  hasSuggestion?: boolean;
}

const ActionPanel: React.FC<ActionPanelProps> = ({
  onAccept,
  onReject,
  onEdit,
  onPrev,
  onNext,
  canGoBack,
  canGoForward,
  isProcessing = false,
  hasSuggestion = true,
}) => {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (isProcessing) return;

      switch (event.key) {
        case 'Enter':
          if (hasSuggestion) {
            onAccept();
          }
          break;
        case 'Escape':
          if (hasSuggestion) {
            onReject();
          }
          break;
        case 'ArrowLeft':
          if (canGoBack) {
            onPrev();
          }
          break;
        case 'ArrowRight':
          if (canGoForward) {
            onNext();
          }
          break;
        default:
          break;
      }
    },
    [isProcessing, hasSuggestion, canGoBack, canGoForward, onAccept, onReject, onPrev, onNext]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      {/* Main Actions */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 1.5 }}>
          Quick Actions
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="success"
            size="large"
            startIcon={<AcceptIcon />}
            onClick={onAccept}
            disabled={isProcessing || !hasSuggestion}
            sx={{ minWidth: 160 }}
          >
            Accept (Enter)
          </Button>
          <Button
            variant="outlined"
            color="error"
            size="large"
            startIcon={<RejectIcon />}
            onClick={onReject}
            disabled={isProcessing || !hasSuggestion}
            sx={{ minWidth: 140 }}
          >
            Reject (Esc)
          </Button>
          {onEdit && (
            <Button
              variant="outlined"
              color="primary"
              size="large"
              startIcon={<EditIcon />}
              onClick={onEdit}
              disabled={isProcessing}
              sx={{ minWidth: 120 }}
            >
              Edit
            </Button>
          )}
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Navigation */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <ButtonGroup variant="outlined" size="large">
          <Tooltip title={canGoBack ? 'Previous Row (Left Arrow)' : 'No previous row'}>
            <span>
              <Button
                startIcon={<PrevIcon />}
                onClick={onPrev}
                disabled={!canGoBack || isProcessing}
              >
                Prev
              </Button>
            </span>
          </Tooltip>
          <Tooltip title={canGoForward ? 'Next Row (Right Arrow)' : 'No more rows'}>
            <span>
              <Button
                endIcon={<NextIcon />}
                onClick={onNext}
                disabled={!canGoForward || isProcessing}
              >
                Next
              </Button>
            </span>
          </Tooltip>
        </ButtonGroup>

        {/* Keyboard Shortcuts Hint */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary' }}>
          <KeyboardIcon fontSize="small" />
          <Typography variant="caption">
            Enter: Accept | Esc: Reject | Arrows: Navigate
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default ActionPanel;
