/**
 * Upload page - Dataset upload and task selection
 */

import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  Stepper,
  Step,
  StepLabel,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CheckCircle as CheckIcon,
  Description as FileIcon,
  Settings as ConfigIcon,
  PlayArrow as StartIcon,
} from '@mui/icons-material';
import { uploadDataset, startJob } from '../services/api';

const steps = ['Select File', 'Configure Task', 'Start Processing'];

const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [taskType, setTaskType] = useState<'easy' | 'medium' | 'hard'>('easy');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDataset, setUploadedDataset] = useState<{ id: string; name: string } | null>(null);

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      const validTypes = ['.csv', '.json', '.xlsx', '.parquet'];
      const fileExt = selectedFile.name.slice(selectedFile.name.lastIndexOf('.')).toLowerCase();
      
      if (!validTypes.includes(fileExt)) {
        setError(`Invalid file type. Please upload: ${validTypes.join(', ')}`);
        return;
      }

      // Validate file size (max 100MB)
      if (selectedFile.size > 100 * 1024 * 1024) {
        setError('File size exceeds 100MB limit');
        return;
      }

      setFile(selectedFile);
      setError(null);
    }
  }, []);

  const handleUpload = async () => {
    if (!file) return;

    try {
      setUploading(true);
      setError(null);

      const dataset = await uploadDataset(file, taskType);
      setUploadedDataset({ id: dataset.id, name: dataset.name });
      setActiveStep(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleStartProcessing = async () => {
    if (!uploadedDataset) return;

    try {
      setUploading(true);
      const job = await startJob(uploadedDataset.id);
      setActiveStep(2);
      
      // Navigate to interactive page after a short delay
      setTimeout(() => {
        navigate(`/interactive/${job.id}`);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start processing');
    } finally {
      setUploading(false);
    }
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Card elevation={2}>
            <CardContent sx={{ p: 4 }}>
              <Box
                sx={{
                  border: '2px dashed',
                  borderColor: 'primary.main',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  bgcolor: 'background.paper',
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: 'action.hover',
                  },
                }}
                component="label"
              >
                <input
                  type="file"
                  hidden
                  accept=".csv,.json,.xlsx,.parquet"
                  onChange={handleFileSelect}
                />
                <UploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Drop your file here or click to browse
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Supports: CSV, JSON, Excel, Parquet (max 100MB)
                </Typography>
              </Box>

              {file && (
                <Box sx={{ mt: 3 }}>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <FileIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={file.name}
                        secondary={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                      />
                    </ListItem>
                  </List>
                  <Button
                    variant="contained"
                    fullWidth
                    onClick={handleUpload}
                    disabled={uploading}
                    startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
                    sx={{ mt: 2 }}
                  >
                    {uploading ? 'Uploading...' : 'Upload Dataset'}
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        );

      case 1:
        return (
          <Card elevation={2}>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h6" gutterBottom>
                Configure Cleaning Task
              </Typography>

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel id="task-type-label">Task Difficulty</InputLabel>
                <Select
                  labelId="task-type-label"
                  value={taskType}
                  label="Task Difficulty"
                  onChange={(e) => setTaskType(e.target.value as 'easy' | 'medium' | 'hard')}
                >
                  <MenuItem value="easy">Easy (Basic cleaning)</MenuItem>
                  <MenuItem value="medium">Medium (Standard cleaning)</MenuItem>
                  <MenuItem value="hard">Hard (Deep cleaning)</MenuItem>
                </Select>
              </FormControl>

              <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
                <strong>Easy:</strong> Handle missing values, duplicates, basic formatting<br />
                <strong>Medium:</strong> + Outliers, category standardization<br />
                <strong>Hard:</strong> + Complex patterns, custom rules, edge cases
              </Typography>

              <Button
                variant="contained"
                fullWidth
                onClick={handleStartProcessing}
                disabled={uploading}
                startIcon={uploading ? <CircularProgress size={20} /> : <StartIcon />}
              >
                {uploading ? 'Starting...' : 'Start Processing'}
              </Button>
            </CardContent>
          </Card>
        );

      case 2:
        return (
          <Card elevation={2}>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <CheckIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
              <Typography variant="h5" gutterBottom>
                Processing Started!
              </Typography>
              <Typography variant="body1" color="textSecondary">
                Redirecting to interactive cleaning session...
              </Typography>
              <CircularProgress sx={{ mt: 3 }} />
            </CardContent>
          </Card>
        );

      default:
        return null;
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 600 }}>
        Upload Dataset
      </Typography>
      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        Upload your data file and configure the cleaning task
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>

      {renderStepContent()}

      {/* Tips */}
      <Paper elevation={1} sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ConfigIcon />
          Tips for Best Results
        </Typography>
        <List dense>
          <ListItem>
            <ListItemText primary="Ensure your file has a header row with column names" />
          </ListItem>
          <ListItem>
            <ListItemText primary="Remove any sensitive data before uploading" />
          </ListItem>
          <ListItem>
            <ListItemText primary="For large files (10MB+), consider splitting into chunks" />
          </ListItem>
          <ListItem>
            <ListItemText primary="CSV files work best for most data cleaning tasks" />
          </ListItem>
        </List>
      </Paper>
    </Box>
  );
};

export default Upload;
