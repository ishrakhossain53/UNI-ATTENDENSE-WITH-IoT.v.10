import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Paper, TextField, Button, Box, Typography, Alert,
  CircularProgress, Container
} from '@mui/material'
import api from '../api.jsx'
import { useAuthStore } from '../store.jsx'

function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuthStore()
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const response = await api.post('/auth/login', { username, password })
      const { token, user } = response.data
      
      login(token, user)
      navigate(`/${user.role}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" sx={{ mb: 4, textAlign: 'center' }}>
          Attendance System Login
        </Typography>
        
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
            sx={{ mt: 3 }}
            disabled={loading || !username || !password}
            onClick={handleSubmit}
          >
            {loading ? <CircularProgress size={24} /> : 'Login'}
          </Button>
        </form>
        
        <Typography variant="body2" sx={{ mt: 3, color: 'text.secondary' }}>
          Demo Credentials:
          <br />Admin: admin / admin123
          <br />Faculty: faculty1 / pass123
          <br />Student: student01 / pass123
        </Typography>
      </Paper>
    </Container>
  )
}

export default Login
