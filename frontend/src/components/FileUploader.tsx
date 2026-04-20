/**
 * FileUploader component - Drag-and-drop file upload with progress
 */

import React, { useCallback, useState, useRef } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Button,
  Alert,
  Paper,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as FileIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

interface FileUploaderProps {
  onUpload: (file: File, taskType: string) => Promise<void>;
  onProgress?: (progress: number) => void;
  disabled?: boolean;
}

interface UploadState {
  file: File | null;
  progress: number;
  status: 'idle' | 'uploading' | 'success' | 'error';
  error: string | null;
}

const ACCEPTED_TYPES = ['.csv', '.json', '.xlsx', '.parquet'];
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

const FileUploader: React.FC<FileUploaderProps> = ({
  onUpload,
  onProgress,
  disabled = false,
}) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    file: null,
    progress: 0,
    status: 'idle',
    error: null,
  });
  const [isDragging, setIsDragging] = useState(false);
  const [taskType, setTaskType] = useState<'easy' | 'medium' | 'hard'>('easy');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      return `Invalid file type. Accepted: ${ACCEPTED_TYPES.join(', ')}`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size exceeds 100MB limit';
    }
    return null;
  };

  const handleFile = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      setUploadState({
        file: null,
        progress: 0,
        status: 'error',
        error,
      });
      return;
    }

    setUploadState({
      file,
      progress: 0,
      status: 'idle',
      error: null,
    });
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [disabled, handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleUpload = async () => {
    if (!uploadState.file) return;

    setUploadState((prev) => ({ ...prev, status: 'uploading', progress: 0, error: null }));

    try {
      // Simulate progress for demo (in real app, use XMLHttpRequest upload events)
      const progressInterval = setInterval(() => {
        setUploadState((prev) => {
          if (prev.progress < 90) {
            const newProgress = prev.progress + Math.random() * 15;
            onProgress?.(Math.min(newProgress, 90));
            return { ...prev, progress: Math.min(newProgress, 90) };
          }
          return prev;
        });
      }, 200);

      await onUpload(uploadState.file, taskType);

      clearInterval(progressInterval);
      setUploadState((prev) => ({ ...prev, progress: 100, status: 'success' }));
      onProgress?.(100);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setUploadState((prev) => ({
        ...prev,
        status: 'error',
        error: errorMessage,
        progress: 0,
      }));
    }
  };

  const handleCancel = () => {
    setUploadState({
      file: null,
      progress: 0,
      status: 'idle',
      error: null,
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <Box>
      {/* Drop Zone */}
      <Paper
        elevation={0}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        sx={{
          border: '2px dashed',
          borderColor: isDragging ? 'primary.main' : uploadState.error ? 'error.main' : 'grey.300',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          bgcolor: isDragging ? 'action.hover' : 'background.paper',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          transition: 'all 0.2s ease',
          '&:hover': !disabled ? {
            borderColor: 'primary.main',
            bgcolor: 'action.hover',
          } : {},
        }}
        component="label"
      >
        <input
          ref={fileInputRef}
          type="file"
          hidden
          accept={ACCEPTED_TYPES.join(',')}
          onChange={handleInputChange}
          disabled={disabled}
        />

        <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
        <Typography variant="h6" gutterBottom>
          {isDragging ? 'Drop file here' : 'Drag & drop your file here'}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          or click to browse
        </Typography>
        <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
          Supports: CSV, JSON, Excel, Parquet (max 100MB)
        </Typography>
      </Paper>

      {/* Selected File */}
      {uploadState.file && (
        <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <FileIcon color="primary" />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1" fontWeight={500}>
                {uploadState.file.name}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {formatFileSize(uploadState.file.size)}
              </Typography>
            </Box>
            {uploadState.status === 'idle' && (
              <Button
                size="small"
                color="error"
                onClick={handleCancel}
                startIcon={<CloseIcon />}
              >
                Remove
              </Button>
            )}
          </Box>
        </Box>
      )}

      {/* Error Message */}
      {uploadState.error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {uploadState.error}
        </Alert>
      )}

      {/* Progress Bar */}
      {uploadState.status === 'uploading' && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant="determinate" value={uploadState.progress} />
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            Uploading... {Math.round(uploadState.progress)}%
          </Typography>
        </Box>
      )}

      {/* Success Message */}
      {uploadState.status === 'success' && (
        <Alert severity="success" sx={{ mt: 2 }}>
          File uploaded successfully!
        </Alert>
      )}

      {/* Task Selection & Upload Button */}
      {uploadState.file && uploadState.status !== 'uploading' && (
        <Box sx={{ mt: 3, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <Box sx={{ minWidth: 200 }}>
            <Typography variant="body2" gutterBottom>
              <strong>Task Difficulty:</strong>
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {(['easy', 'medium', 'hard'] as const).map((type) => (
                <Button
                  key={type}
                  variant={taskType === type ? 'contained' : 'outlined'}
                  size="small"
                  onClick={() => setTaskType(type)}
                  disabled={disabled}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Button>
              ))}
            </Box>
          </Box>

          <Box sx={{ flex: 1 }} />

          <Button
            variant="contained"
            size="large"
            onClick={handleUpload}
            disabled={disabled || !uploadState.file}
            startIcon={<UploadIcon />}
          >
            Upload & Start Cleaning
          </Button>
        </Box>
      )}

      {/* Task Description */}
      {uploadState.file && uploadState.status !== 'uploading' && (
        <Box sx={{ mt: 2, p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
          <Typography variant="body2">
            <strong>{taskType.charAt(0).toUpperCase() + taskType.slice(1)} task:</strong>{' '}
            {taskType === 'easy' && 'Handle missing values, duplicates, basic formatting'}
            {taskType === 'medium' && 'Easy + Outliers, category standardization'}
            {taskType === 'hard' && 'Medium + Complex patterns, custom rules, edge cases'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default FileUploader;
