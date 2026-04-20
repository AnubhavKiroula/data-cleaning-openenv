/**
 * Upload page - Dataset upload and task selection
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Alert,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import {
  Settings as ConfigIcon,
} from '@mui/icons-material';
import FileUploader from '../components/FileUploader';
import DatasetPreview from '../components/DatasetPreview';
import { uploadDataset, startJob } from '../services/api';
import type { UploadResponse } from '../types';

const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [uploadedDataset, setUploadedDataset] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file: File, taskType: string) => {
    try {
      setUploading(true);
      setError(null);

      const response = await uploadDataset(file, taskType);
      setUploadedDataset(response);

      // Auto-start job after successful upload
      const job = await startJob(response.id);
      
      // Navigate to interactive page
      navigate(`/interactive/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      throw err;
    } finally {
      setUploading(false);
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

      {/* File Uploader */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Select File
        </Typography>
        <FileUploader onUpload={handleUpload} disabled={uploading} />
      </Paper>

      {/* Dataset Preview (after upload) */}
      {uploadedDataset && (
        <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
          <DatasetPreview dataset={uploadedDataset} />
        </Paper>
      )}

      {/* Tips */}
      <Paper elevation={1} sx={{ p: 3 }}>
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
