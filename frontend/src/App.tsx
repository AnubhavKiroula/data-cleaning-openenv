/**
 * Main App component with React Router setup
 * Phase 3.1 - React Frontend Setup
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';

// Components
import Navigation from './components/Navigation';
import Sidebar from './components/Sidebar';

// Pages
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Jobs from './pages/Jobs';
import Interactive from './pages/Interactive';

// Create Material-UI theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#9c27b0',
      light: '#ba68c8',
      dark: '#7b1fa2',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          {/* Top Navigation */}
          <Navigation />
          
          {/* Main Content Area */}
          <Box sx={{ display: 'flex', flex: 1 }}>
            {/* Sidebar */}
            <Sidebar />
            
            {/* Page Content */}
            <Box
              component="main"
              sx={{
                flexGrow: 1,
                p: 3,
                bgcolor: 'background.default',
                minHeight: 'calc(100vh - 64px)', // Subtract header height
              }}
            >
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/jobs" element={<Jobs />} />
                <Route path="/interactive/:jobId" element={<Interactive />} />
              </Routes>
            </Box>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App
