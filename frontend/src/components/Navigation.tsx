/**
 * Navigation component - App header with logo and navigation links
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  CloudUpload as UploadIcon,
  History as HistoryIcon,
  CleaningServices as LogoIcon,
} from '@mui/icons-material';

const Navigation: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
    { path: '/upload', label: 'Upload', icon: <UploadIcon /> },
    { path: '/jobs', label: 'History', icon: <HistoryIcon /> },
  ];

  const isActive = (path: string): boolean => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <AppBar position="static" elevation={1} sx={{ bgcolor: 'primary.main' }}>
      <Toolbar>
        {/* Logo */}
        <IconButton
          edge="start"
          color="inherit"
          aria-label="logo"
          component={Link}
          to="/"
          sx={{ mr: 2 }}
        >
          <LogoIcon fontSize="large" />
        </IconButton>

        {/* App Title */}
        <Typography
          variant="h6"
          component={Link}
          to="/"
          sx={{
            flexGrow: 1,
            textDecoration: 'none',
            color: 'inherit',
            fontWeight: 600,
          }}
        >
          DataClean AI
        </Typography>

        {/* Navigation Links */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              component={Link}
              to={item.path}
              color="inherit"
              startIcon={item.icon}
              sx={{
                bgcolor: isActive(item.path) ? 'rgba(255,255,255,0.15)' : 'transparent',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.25)',
                },
                px: 2,
                py: 1,
                borderRadius: 1,
                fontWeight: isActive(item.path) ? 600 : 400,
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>

        {/* User Profile (placeholder) */}
        <Box sx={{ ml: 2 }}>
          <IconButton color="inherit" aria-label="user profile">
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              User
            </Typography>
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navigation;
