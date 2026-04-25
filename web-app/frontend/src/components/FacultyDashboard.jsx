import React, { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Chip,
  Stack
} from '@mui/material'
import api from '../api.jsx'

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ py: 2 }}>{children}</Box> : null
}

function FacultyDashboard() {
  const [tabIndex, setTabIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [profile, setProfile] = useState(null)
  const [courses, setCourses] = useState([])
  const [selectedCourseId, setSelectedCourseId] = useState('')
  const [courseReport, setCourseReport] = useState(null)

  const [threshold, setThreshold] = useState(75)
  const [thresholdInput, setThresholdInput] = useState('75')

  const [pastRecords, setPastRecords] = useState([])
  const [pastLoading, setPastLoading] = useState(false)
  const [pastFilters, setPastFilters] = useState({
    date_from: new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0],
    date_to: new Date().toISOString().split('T')[0],
    student_name_filter: ''
  })

  useEffect(() => {
    loadBaseData()
  }, [])

  useEffect(() => {
    if (selectedCourseId) {
      loadCourseReport(selectedCourseId)
    }
  }, [selectedCourseId])

  const selectedCourse = useMemo(
    () => courses.find((course) => course.course_id === selectedCourseId),
    [courses, selectedCourseId]
  )

  const loadBaseData = async () => {
    setLoading(true)
    setError('')
    try {
      const [profileRes, thresholdRes] = await Promise.all([
        api.get('/users/me/profile'),
        api.get('/settings/threshold')
      ])

      const profileData = profileRes.data || {}
      setProfile(profileData)
      setCourses(profileData.courses || [])

      const thresholdValue = thresholdRes.data?.threshold || 75
      setThreshold(thresholdValue)
      setThresholdInput(String(thresholdValue))

      if ((profileData.courses || []).length > 0) {
        setSelectedCourseId(profileData.courses[0].course_id)
      }
    } catch {
      setError('Failed to load faculty data')
    } finally {
      setLoading(false)
    }
  }

  const loadCourseReport = async (courseId) => {
    try {
      const res = await api.get(`/reports/course/${courseId}`)
      setCourseReport(res.data || null)
    } catch {
      setError('Failed to load course report')
    }
  }

  const loadPastAttendance = async () => {
    setPastLoading(true)
    try {
      const params = new URLSearchParams()
      if (pastFilters.date_from) params.append('date_from', pastFilters.date_from)
      if (pastFilters.date_to) params.append('date_to', pastFilters.date_to)
      const res = await api.get(`/attendance/history?${params.toString()}`)
      setPastRecords(res.data || [])
    } catch {
      setError('Failed to load attendance history')
    } finally {
      setPastLoading(false)
    }
  }

  const saveThreshold = async () => {
    const val = parseInt(thresholdInput, 10)
    if (Number.isNaN(val) || val < 1 || val > 100) {
      setError('Threshold must be between 1 and 100')
      return
    }

    try {
      await api.post('/settings/threshold', { threshold: val })
      setThreshold(val)
      setSuccess(`Threshold updated to ${val}%`)
    } catch {
      setError('Failed to update threshold')
    }
  }

  const filteredPastRecords = useMemo(() => (
    pastRecords.filter((r) => (
      !pastFilters.student_name_filter ||
      r.student_name?.toLowerCase().includes(pastFilters.student_name_filter.toLowerCase())
    ))
  ), [pastRecords, pastFilters.student_name_filter])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 12 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Faculty Studio</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Track course attendance health, detect risk early, and keep class operations aligned.
      </Typography>

      {error ? <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert> : null}
      {success ? <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert> : null}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
          <Typography variant="h6" sx={{ flex: 1 }}>Attendance Threshold</Typography>
          <TextField
            label="Threshold %"
            type="number"
            size="small"
            value={thresholdInput}
            onChange={(e) => setThresholdInput(e.target.value)}
            inputProps={{ min: 1, max: 100 }}
            sx={{ width: 140 }}
          />
          <Button variant="contained" onClick={saveThreshold}>Save</Button>
          <Chip label={`Current ${threshold}%`} />
        </Stack>
      </Paper>

      <Tabs value={tabIndex} onChange={(e, v) => setTabIndex(v)}>
        <Tab label="Course Insights" />
        <Tab label="Past Attendance" />
        <Tab label="At-Risk Students" />
      </Tabs>

      <TabPanel value={tabIndex} index={0}>
        <Paper sx={{ p: 2, mb: 2 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
            <Typography variant="h6" sx={{ minWidth: 180 }}>Select Course</Typography>
            <TextField
              select
              SelectProps={{ native: true }}
              size="small"
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              sx={{ minWidth: 260 }}
            >
              <option value="">Choose a course</option>
              {courses.map((course) => (
                <option key={course.course_id} value={course.course_id}>
                  {course.course_code} - {course.course_name}
                </option>
              ))}
            </TextField>
          </Stack>
        </Paper>

        {selectedCourse && courseReport ? (
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">Course</Typography>
                  <Typography variant="h6">{courseReport.course_name}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">Attendance %</Typography>
                  <Typography variant="h5">{courseReport.attendance_pct || 0}%</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">Enrolled Students</Typography>
                  <Typography variant="h5">{courseReport.total_enrolled || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Paper sx={{ p: 3 }}>
            <Typography color="text.secondary">Select a course to view insights.</Typography>
          </Paper>
        )}
      </TabPanel>

      <TabPanel value={tabIndex} index={1}>
        <Paper sx={{ p: 2, mb: 2 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
            <TextField
              label="From"
              type="date"
              size="small"
              value={pastFilters.date_from}
              onChange={(e) => setPastFilters({ ...pastFilters, date_from: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="To"
              type="date"
              size="small"
              value={pastFilters.date_to}
              onChange={(e) => setPastFilters({ ...pastFilters, date_to: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Student name"
              size="small"
              value={pastFilters.student_name_filter}
              onChange={(e) => setPastFilters({ ...pastFilters, student_name_filter: e.target.value })}
            />
            <Button variant="contained" onClick={loadPastAttendance}>Search</Button>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          {pastLoading ? <CircularProgress /> : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date & Time</TableCell>
                    <TableCell>Student</TableCell>
                    <TableCell>Room</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Match Score</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredPastRecords.map((rec) => (
                    <TableRow key={rec.record_id}>
                      <TableCell>{new Date(rec.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{rec.student_name}</TableCell>
                      <TableCell>{rec.room_number}</TableCell>
                      <TableCell>{rec.status}</TableCell>
                      <TableCell>{rec.match_score ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </TabPanel>

      <TabPanel value={tabIndex} index={2}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>
            At-Risk Students {selectedCourse ? `for ${selectedCourse.course_name}` : ''}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Students below {threshold}% threshold are highlighted for intervention.
          </Typography>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Student Number</TableCell>
                  <TableCell>Attendance %</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(courseReport?.at_risk_students || []).map((student) => (
                  <TableRow key={student.student_id}>
                    <TableCell>{student.full_name}</TableCell>
                    <TableCell>{student.student_number}</TableCell>
                    <TableCell>{student.attendance_pct}%</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={student.attendance_pct < 60 ? 'Critical' : 'At Risk'}
                        color={student.attendance_pct < 60 ? 'error' : 'warning'}
                      />
                    </TableCell>
                  </TableRow>
                ))}
                {(courseReport?.at_risk_students || []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography color="text.secondary">No at-risk students for the selected course.</Typography>
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </TabPanel>
    </Box>
  )
}

export default FacultyDashboard
