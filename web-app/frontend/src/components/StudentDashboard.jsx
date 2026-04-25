import React, { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress
} from '@mui/material'
import api from '../api.jsx'

function StudentDashboard() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [profile, setProfile] = useState(null)
  const [enrollment, setEnrollment] = useState(null)
  const [attendance, setAttendance] = useState([])
  const [report, setReport] = useState({ courses: [] })
  const [threshold, setThreshold] = useState(75)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const profileRes = await api.get('/users/me/profile')
      const profileData = profileRes.data || {}
      setProfile(profileData)

      const studentId = profileData.student_id
      if (!studentId) {
        throw new Error('Student profile missing student_id')
      }

      const [enrollmentRes, attendanceRes, reportRes, thresholdRes] = await Promise.all([
        api.get(`/enrollment/status/${studentId}`),
        api.get(`/attendance/student/${studentId}`),
        api.get(`/reports/student/${studentId}`),
        api.get('/settings/threshold')
      ])

      setEnrollment(enrollmentRes.data)
      setAttendance(attendanceRes.data || [])
      setReport(reportRes.data || { courses: [] })
      setThreshold(thresholdRes.data?.threshold || 75)
    } catch {
      setError('Failed to load student dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const courses = report.courses || []

  const overallPct = useMemo(() => {
    if (!courses.length) return 0
    const total = courses.reduce((sum, c) => sum + (c.attendance_pct || 0), 0)
    return Math.round(total / courses.length)
  }, [courses])

  const belowThreshold = useMemo(
    () => courses.filter((course) => (course.attendance_pct || 0) < threshold),
    [courses, threshold]
  )

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 12 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Student View</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Track your attendance health across courses and stay ahead of threshold alerts.
      </Typography>

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Student</Typography>
              <Typography variant="h6">{profile?.full_name || profile?.username || 'Student'}</Typography>
              <Typography variant="body2" color="text.secondary">{profile?.student_number || 'N/A'}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Overall Attendance</Typography>
              <Typography variant="h5">{overallPct}%</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Biometric Enrollment</Typography>
              <Chip
                size="small"
                label={enrollment?.fp_enrolled ? 'Enrolled' : 'Not Enrolled'}
                color={enrollment?.fp_enrolled ? 'success' : 'default'}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {belowThreshold.length > 0 ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          You are below {threshold}% in: {belowThreshold.map((c) => c.course_name).join(', ')}
        </Alert>
      ) : null}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1.5 }}>Course Breakdown</Typography>
        {courses.length === 0 ? (
          <Typography color="text.secondary">No course report data available.</Typography>
        ) : (
          courses.map((course) => {
            const pct = Math.round(course.attendance_pct || 0)
            return (
              <Box key={course.course_id} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">{course.course_name}</Typography>
                  <Typography variant="body2">{course.present}/{course.total} ({pct}%)</Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={pct}
                  sx={{
                    height: 8,
                    borderRadius: 99,
                    bgcolor: 'rgba(0,0,0,0.08)',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: pct >= threshold ? 'success.main' : pct >= 60 ? 'warning.main' : 'error.main'
                    }
                  }}
                />
              </Box>
            )
          })
        )}
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1.5 }}>Recent Attendance</Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Room</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Method</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {attendance.slice(0, 20).map((rec) => (
                <TableRow key={rec.record_id}>
                  <TableCell>{new Date(rec.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{rec.room_number || rec.classroom_id}</TableCell>
                  <TableCell>{rec.status}</TableCell>
                  <TableCell>{rec.verification_method}</TableCell>
                </TableRow>
              ))}
              {attendance.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography color="text.secondary">No attendance records yet.</Typography>
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  )
}

export default StudentDashboard
