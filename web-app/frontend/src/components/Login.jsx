import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Paper, TextField, Button, Box, Typography, Alert,
  CircularProgress, Container, Stack
} from '@mui/material'
import api from '../api.jsx'
import { useAuthStore } from '../store.jsx'

function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [healthChecking, setHealthChecking] = useState(true)
  const [dbUnavailable, setDbUnavailable] = useState(false)
  const { login } = useAuthStore()

  useEffect(() => {
    const checkDbHealth = async () => {
      setHealthChecking(true)
      setDbUnavailable(false)
      try {
        await api.get('/health/db')
      } catch (err) {
        if (err.response?.status === 503) {
          setDbUnavailable(true)
        }
      } finally {
        setHealthChecking(false)
      }
    }

    checkDbHealth()
  }, [])
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      if (dbUnavailable) {
        return
      }
      const response = await api.post('/auth/login', { username, password })
      const { token, user } = response.data
      
      login(token, user)
      navigate(`/${user.role}`)
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Invalid username or password. If you are a new user, contact your administrator.')
      } else {
        setError(err.response?.data?.detail || 'Login failed')
      }
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Container maxWidth="md" sx={{ mt: { xs: 2, md: 6 } }}>
      <Paper sx={{ p: { xs: 3, md: 5 }, borderRadius: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={4} alignItems="stretch">
          <Box sx={{ flex: 1 }}>
            <Typography variant="h4" sx={{ mb: 1.5 }}>
              Welcome Back
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Sign in to access live attendance streams, enrollment controls, and reports.
            </Typography>

            {healthChecking && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Checking system status...
              </Alert>
            )}

            {!healthChecking && dbUnavailable && (
              <Alert severity="error" sx={{ mb: 2 }}>
                Database unavailable. Contact administrator.
              </Alert>
            )}

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                margin="normal"
                disabled={loading}
                autoFocus
              />

              <TextField
                fullWidth
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                margin="normal"
                disabled={loading}
              />

              <Button
                fullWidth
                variant="contained"
                sx={{
                  mt: 3,
                  py: 1.2,
                  bgcolor: 'primary.main',
                  '&:hover': { bgcolor: '#cf2d56' }
                }}
                disabled={loading || healthChecking || dbUnavailable || !username || !password}
                onClick={handleSubmit}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : 'Login'}
              </Button>
            </form>
          </Box>

          <Box
            sx={{
              flex: 1,
              p: 3,
              borderRadius: 2,
              bgcolor: 'background.default',
              border: '1px solid',
              borderColor: 'divider'
            }}
          >
            <Typography variant="h6" sx={{ mb: 1.5 }}>
              Demo Credentials
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Admin: admin / admin123
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Faculty: faculty1 / pass123
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Student: student01 / pass123
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
              Designed with warm surfaces, editorial typography, and a focused control layout inspired by your design system.
            </Typography>
          </Box>
        </Stack>
      </Paper>
    </Container>
  )
}

export default Login
