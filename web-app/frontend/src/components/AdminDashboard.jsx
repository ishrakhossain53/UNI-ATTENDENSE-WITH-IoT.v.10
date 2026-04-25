import React, { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Grid,
  Paper,
  Typography,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Alert,
  Chip,
  CircularProgress,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Card,
  CardContent,
  Stack
} from '@mui/material'
import api from '../api.jsx'
import { useAttendanceStore } from '../store.jsx'

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ py: 2 }}>{children}</Box> : null
}

function MetricCard({ label, value, helper }) {
  return (
    <Card sx={{ bgcolor: 'background.paper' }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">{label}</Typography>
        <Typography variant="h5" sx={{ mb: 0.5 }}>{value}</Typography>
        {helper ? <Typography variant="body2" color="text.secondary">{helper}</Typography> : null}
      </CardContent>
    </Card>
  )
}

function AdminDashboard() {
  const [tabIndex, setTabIndex] = useState(0)
  const [students, setStudents] = useState([])
  const [devices, setDevices] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [enrollDialog, setEnrollDialog] = useState(false)
  const [selectedStudent, setSelectedStudent] = useState(null)

  const [pastRecords, setPastRecords] = useState([])
  const [pastLoading, setPastLoading] = useState(false)
  const [pastFilters, setPastFilters] = useState({
    date_from: new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0],
    date_to: new Date().toISOString().split('T')[0],
    student_id: ''
  })

  const [editAttendanceDialog, setEditAttendanceDialog] = useState(false)
  const [selectedAttendance, setSelectedAttendance] = useState(null)
  const [attendanceEditData, setAttendanceEditData] = useState({
    status: 'present',
    verification_method: 'fingerprint',
    timestamp: ''
  })

  const recentScans = useAttendanceStore((state) => state.recentScans)

  useEffect(() => {
    loadData()

    const token = localStorage.getItem('auth_token')
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/attendance?token=${token}`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.event === 'attendance_scan') {
        useAttendanceStore.getState().addScan(data)
      }
    }

    return () => ws.close()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const [studentsRes, devicesRes, statsRes] = await Promise.all([
        api.get('/students'),
        api.get('/devices'),
        api.get('/attendance/stats')
      ])
      setStudents(studentsRes.data || [])
      setDevices(devicesRes.data || [])
      setStats(statsRes.data || {})
    } catch (err) {
      setError('Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }

  const handleEnroll = async () => {
    if (!selectedStudent) return
    try {
      if (selectedStudent.fp_enrolled) {
        await api.delete(`/enrollment/revoke/${selectedStudent.student_id}`)
        setSuccess('Fingerprint enrollment revoked successfully')
      } else {
        const template = btoa(Math.random().toString())
        await api.post('/enrollment/enroll', {
          student_id: selectedStudent.student_id,
          template_data_base64: template
        })
        setSuccess('Fingerprint enrolled successfully')
      }
      setEnrollDialog(false)
      setSelectedStudent(null)
      await loadData()
    } catch {
      setError('Enrollment action failed')
    }
  }

  const loadPastAttendance = async () => {
    setPastLoading(true)
    try {
      const params = new URLSearchParams()
      if (pastFilters.date_from) params.append('date_from', pastFilters.date_from)
      if (pastFilters.date_to) params.append('date_to', pastFilters.date_to)
      if (pastFilters.student_id) params.append('student_id', pastFilters.student_id)
      const res = await api.get(`/attendance/history?${params.toString()}`)
      setPastRecords(res.data || [])
    } catch {
      setError('Failed to load attendance history')
    } finally {
      setPastLoading(false)
    }
  }

  const handleDeleteAttendance = async (recordId) => {
    if (!window.confirm('Delete this attendance record?')) return
    try {
      await api.delete(`/attendance/${recordId}`)
      setSuccess('Attendance record deleted')
      await loadPastAttendance()
    } catch {
      setError('Failed to delete attendance record')
    }
  }

  const handleEditAttendance = (record) => {
    setSelectedAttendance(record)
    setAttendanceEditData({
      status: record.status,
      verification_method: record.verification_method,
      timestamp: new Date(record.timestamp).toISOString().slice(0, 16)
    })
    setEditAttendanceDialog(true)
  }

  const handleSaveAttendanceEdit = async () => {
    if (!selectedAttendance) return
    try {
      await api.put(`/attendance/${selectedAttendance.record_id}`, attendanceEditData)
      setEditAttendanceDialog(false)
      setSuccess('Attendance record updated')
      await loadPastAttendance()
    } catch {
      setError('Failed to update attendance record')
    }
  }

  const enrolledCount = useMemo(() => students.filter((s) => s.fp_enrolled).length, [students])

  if (loading || !stats) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 12 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Admin Control Desk</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Monitor live scans, manage enrollment, and curate attendance records from one place.
      </Typography>

      {error ? <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert> : null}
      {success ? <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert> : null}

      <Tabs value={tabIndex} onChange={(e, v) => setTabIndex(v)} sx={{ mb: 1.5 }}>
        <Tab label="Overview" />
        <Tab label="Enrollment" />
        <Tab label="Attendance" />
        <Tab label="Devices" />
      </Tabs>

      <TabPanel value={tabIndex} index={0}>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={6} md={3}><MetricCard label="Total Students" value={students.length} /></Grid>
          <Grid item xs={12} sm={6} md={3}><MetricCard label="Enrolled" value={enrolledCount} /></Grid>
          <Grid item xs={12} sm={6} md={3}><MetricCard label="Active Devices" value={devices.length} /></Grid>
          <Grid item xs={12} sm={6} md={3}><MetricCard label="Scans Today" value={stats.total_scans_today || 0} /></Grid>
        </Grid>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>Live Attendance Stream</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Student</TableCell>
                  <TableCell>Course</TableCell>
                  <TableCell>Room</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentScans.slice(0, 20).map((scan, idx) => (
                  <TableRow key={`${scan.student_id}-${scan.timestamp}-${idx}`}>
                    <TableCell>{new Date(scan.timestamp).toLocaleTimeString()}</TableCell>
                    <TableCell>{scan.student_name || '-'}</TableCell>
                    <TableCell>{scan.course_name || '-'}</TableCell>
                    <TableCell>{scan.room_number || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </TabPanel>

      <TabPanel value={tabIndex} index={1}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>Fingerprint Enrollment</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Student</TableCell>
                  <TableCell>Student Number</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {students.map((student) => (
                  <TableRow key={student.student_id}>
                    <TableCell>{student.full_name}</TableCell>
                    <TableCell>{student.student_number}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={student.fp_enrolled ? 'Enrolled' : 'Not Enrolled'}
                        color={student.fp_enrolled ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        variant="outlined"
                        onClick={() => {
                          setSelectedStudent(student)
                          setEnrollDialog(true)
                        }}
                      >
                        {student.fp_enrolled ? 'Revoke' : 'Enroll'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </TabPanel>

      <TabPanel value={tabIndex} index={2}>
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
              label="Student ID"
              size="small"
              value={pastFilters.student_id}
              onChange={(e) => setPastFilters({ ...pastFilters, student_id: e.target.value })}
            />
            <Button variant="contained" onClick={loadPastAttendance}>Search</Button>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>Past Attendance Records</Typography>
          {pastLoading ? <CircularProgress /> : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Student</TableCell>
                    <TableCell>Room</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pastRecords.map((rec) => (
                    <TableRow key={rec.record_id}>
                      <TableCell>{new Date(rec.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{rec.student_name}</TableCell>
                      <TableCell>{rec.room_number}</TableCell>
                      <TableCell>{rec.status}</TableCell>
                      <TableCell>{rec.verification_method}</TableCell>
                      <TableCell align="right">
                        <Button size="small" onClick={() => handleEditAttendance(rec)}>Edit</Button>
                        <Button size="small" color="error" onClick={() => handleDeleteAttendance(rec.record_id)}>Delete</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </TabPanel>

      <TabPanel value={tabIndex} index={3}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>Device Fleet</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Device ID</TableCell>
                  <TableCell>Classroom</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Gateway</TableCell>
                  <TableCell>Queue Depth</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {devices.map((device) => (
                  <TableRow key={device.device_id}>
                    <TableCell>{device.device_id}</TableCell>
                    <TableCell>{device.classroom}</TableCell>
                    <TableCell>
                      <Chip size="small" label={device.status} color={device.status === 'online' ? 'success' : 'default'} />
                    </TableCell>
                    <TableCell>{device.gateway_id || '-'}</TableCell>
                    <TableCell>{device.queue_depth ?? 0}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </TabPanel>

      <Dialog open={enrollDialog} onClose={() => setEnrollDialog(false)}>
        <DialogTitle>{selectedStudent?.fp_enrolled ? 'Revoke Enrollment' : 'Enroll Fingerprint'}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {selectedStudent?.full_name} ({selectedStudent?.student_number})
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnrollDialog(false)}>Cancel</Button>
          <Button variant="contained" color={selectedStudent?.fp_enrolled ? 'error' : 'primary'} onClick={handleEnroll}>
            {selectedStudent?.fp_enrolled ? 'Revoke' : 'Confirm'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editAttendanceDialog} onClose={() => setEditAttendanceDialog(false)}>
        <DialogTitle>Edit Attendance</DialogTitle>
        <DialogContent sx={{ minWidth: 360, pt: 2 }}>
          <TextField
            fullWidth
            select
            SelectProps={{ native: true }}
            size="small"
            sx={{ mb: 1.5 }}
            label="Status"
            value={attendanceEditData.status}
            onChange={(e) => setAttendanceEditData({ ...attendanceEditData, status: e.target.value })}
          >
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="manual">Manual</option>
          </TextField>
          <TextField
            fullWidth
            select
            SelectProps={{ native: true }}
            size="small"
            sx={{ mb: 1.5 }}
            label="Verification"
            value={attendanceEditData.verification_method}
            onChange={(e) => setAttendanceEditData({ ...attendanceEditData, verification_method: e.target.value })}
          >
            <option value="fingerprint">Fingerprint</option>
            <option value="manual">Manual</option>
            <option value="rfid">RFID</option>
          </TextField>
          <TextField
            fullWidth
            size="small"
            type="datetime-local"
            label="Timestamp"
            InputLabelProps={{ shrink: true }}
            value={attendanceEditData.timestamp}
            onChange={(e) => setAttendanceEditData({ ...attendanceEditData, timestamp: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAttendanceDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveAttendanceEdit}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default AdminDashboard
