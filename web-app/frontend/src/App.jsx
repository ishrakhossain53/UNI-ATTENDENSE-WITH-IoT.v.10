import React, { useEffect, useMemo, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Button,
  Chip,
  Container,
  IconButton,
  Tooltip,
  ThemeProvider,
  CssBaseline,
  GlobalStyles,
  createTheme
} from '@mui/material'
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded'
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded'
import { useAuthStore } from './store.jsx'
import Login from './components/Login.jsx'
import AdminDashboard from './components/AdminDashboard.jsx'
import FacultyDashboard from './components/FacultyDashboard.jsx'
import StudentDashboard from './components/StudentDashboard.jsx'

const THEME_KEY = 'ui-theme-mode'

const getTheme = (mode) => createTheme({
  palette: {
    mode,
    primary: { main: '#f54e00' },
    error: { main: '#cf2d56' },
    success: { main: '#1f8a65' },
    background: mode === 'light'
      ? { default: '#f2f1ed', paper: '#e6e5e0' }
      : { default: '#1f1d18', paper: '#2a2721' },
    text: mode === 'light'
      ? { primary: '#26251e', secondary: 'rgba(38,37,30,0.65)' }
      : { primary: '#f2f1ed', secondary: 'rgba(242,241,237,0.72)' },
    divider: mode === 'light' ? 'rgba(38,37,30,0.16)' : 'rgba(242,241,237,0.18)'
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Franklin Gothic Medium", "Arial Narrow", system-ui, sans-serif',
    h4: { fontWeight: 500, letterSpacing: '-0.03em' },
    h5: { fontWeight: 500, letterSpacing: '-0.02em' },
    h6: { fontWeight: 500, letterSpacing: '-0.01em' },
    body1: { fontFamily: '"Palatino Linotype", "Book Antiqua", Palatino, serif' },
    body2: { fontFamily: '"Palatino Linotype", "Book Antiqua", Palatino, serif' },
    button: { textTransform: 'none', letterSpacing: '0.02em', fontWeight: 500 }
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          border: '1px solid',
          borderColor: mode === 'light' ? 'rgba(38,37,30,0.12)' : 'rgba(242,241,237,0.16)',
          boxShadow: mode === 'light'
            ? 'rgba(0,0,0,0.06) 0px 18px 44px'
            : 'rgba(0,0,0,0.36) 0px 18px 44px'
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 9999 }
      }
    }
  }
})

function NavBar({ mode, toggleMode }) {
  const { user, logout } = useAuthStore()

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        mb: 4,
        bgcolor: mode === 'light' ? 'rgba(242,241,237,0.86)' : 'rgba(31,29,24,0.86)',
        color: 'text.primary',
        borderBottom: '1px solid',
        borderColor: 'divider',
        backdropFilter: 'blur(10px)'
      }}
    >
      <Toolbar sx={{ minHeight: 72 }}>
        <Typography variant="h6" sx={{ flex: 1, letterSpacing: '-0.02em' }}>
          Attendance Studio
        </Typography>

        <Tooltip title={mode === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}>
          <IconButton onClick={toggleMode} sx={{ mr: 1, bgcolor: 'background.paper' }}>
            {mode === 'light' ? <DarkModeRoundedIcon /> : <LightModeRoundedIcon />}
          </IconButton>
        </Tooltip>

        {user && (
          <>
            <Typography variant="body2" sx={{ mr: 2 }}>
              {user.username}
            </Typography>
            <Chip
              label={user.role.toUpperCase()}
              size="small"
              sx={{
                mr: 1.5,
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider'
              }}
            />
            <Button
              variant="outlined"
              color="inherit"
              onClick={() => {
                logout()
                window.location.href = '/'
              }}
            >
              Logout
            </Button>
          </>
        )}
      </Toolbar>
    </AppBar>
  )
}

function ProtectedRoute({ children, requiredRole }) {
  const { token, user } = useAuthStore()
  
  if (!token || !user) {
    return <Navigate to="/" replace />
  }
  
  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to="/" replace />
  }
  
  return children
}

function App() {
  const { token, initializeFromStorage } = useAuthStore()
  const [mode, setMode] = useState(localStorage.getItem(THEME_KEY) || 'light')
  const theme = useMemo(() => getTheme(mode), [mode])

  useEffect(() => {
    initializeFromStorage()
  }, [])

  const toggleMode = () => {
    const next = mode === 'light' ? 'dark' : 'light'
    setMode(next)
    localStorage.setItem(THEME_KEY, next)
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <GlobalStyles styles={{
        body: {
          backgroundImage: mode === 'light'
            ? 'radial-gradient(circle at 0% 0%, rgba(245,78,0,0.08), transparent 36%), radial-gradient(circle at 100% 100%, rgba(192,168,221,0.14), transparent 42%)'
            : 'radial-gradient(circle at 10% 10%, rgba(245,78,0,0.12), transparent 38%), radial-gradient(circle at 92% 88%, rgba(159,187,224,0.12), transparent 45%)'
        }
      }} />
      <BrowserRouter>
        <NavBar mode={mode} toggleMode={toggleMode} />
        <Container maxWidth="lg" sx={{ pb: 6 }}>
          <Routes>
            <Route path="/" element={!token ? <Login /> : <Navigate to={`/${useAuthStore.getState().user?.role}`} replace />} />

            <Route
              path="/admin"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />

            <Route
              path="/faculty"
              element={
                <ProtectedRoute requiredRole="faculty">
                  <FacultyDashboard />
                </ProtectedRoute>
              }
            />

            <Route
              path="/student"
              element={
                <ProtectedRoute requiredRole="student">
                  <StudentDashboard />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Container>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
