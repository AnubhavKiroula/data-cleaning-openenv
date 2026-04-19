/**
 * Sidebar component - Side navigation with quick actions and stats summary
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Button,
  Paper,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  CloudUpload as UploadIcon,
  History as HistoryIcon,
  PlayArrow as StartIcon,
  Analytics as StatsIcon,
} from '@mui/icons-material';

const DRAWER_WIDTH = 240;

interface SidebarProps {
  stats?: {
    totalJobs?: number;
    completedJobs?: number;
    avgAccuracy?: number;
  };
}

const Sidebar: React.FC<SidebarProps> = ({ stats }) => {
  const location = useLocation();

  const menuItems = [
    { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
    { path: '/upload', label: 'Upload Dataset', icon: <UploadIcon /> },
    { path: '/jobs', label: 'Job History', icon: <HistoryIcon /> },
  ];

  const isActive = (path: string): boolean => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          bgcolor: 'background.default',
          borderRight: '1px solid',
          borderColor: 'divider',
        },
      }}
    >
      {/* Quick Stats Section */}
      {stats && (
        <Box sx={{ p: 2 }}>
          <Paper elevation={0} sx={{ p: 2, bgcolor: 'primary.light', color: 'primary.contrastText' }}>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              Quick Stats
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Total Jobs:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {stats.totalJobs || 0}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Completed:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {stats.completedJobs || 0}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Avg Accuracy:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {stats.avgAccuracy ? `${stats.avgAccuracy.toFixed(1)}%` : 'N/A'}
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Box>
      )}

      <Divider />

      {/* Main Navigation */}
      <List sx={{ px: 1 }}>
        {menuItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              component={Link}
              to={item.path}
              selected={isActive(item.path)}
              sx={{
                borderRadius: 1,
                mb: 0.5,
                '&.Mui-selected': {
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    bgcolor: 'primary.dark',
                  },
                  '& .MuiListItemIcon-root': {
                    color: 'inherit',
                  },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider sx={{ my: 1 }} />

      {/* Quick Actions */}
      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'text.secondary' }}>
          Quick Actions
        </Typography>
        <Button
          variant="contained"
          fullWidth
          component={Link}
          to="/upload"
          startIcon={<StartIcon />}
          sx={{ mb: 1 }}
        >
          New Job
        </Button>
        <Button
          variant="outlined"
          fullWidth
          component={Link}
          to="/jobs"
          startIcon={<StatsIcon />}
        >
          View Reports
        </Button>
      </Box>
    </Drawer>
  );
};

export default Sidebar;
