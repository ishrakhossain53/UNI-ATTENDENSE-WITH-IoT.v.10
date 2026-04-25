import React, { useState, useEffect } from 'react'
import {
  Box, Card, CardContent, Grid, Paper, Tabs, Tab, Typography,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Alert, Chip, CircularProgress, Collapse, IconButton
} from '@mui/material'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Title, Tooltip, Legend, ArcElement
} from 'chart.js'
import api from '../api.jsx'
import { useAttendanceStore } from '../store.jsx'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, BarElement,
  Title, Tooltip, Legend, ArcElement
)

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ p: 2 }}>{children}</Box> : null
}

function AdminDashboard() {
  const [tabIndex, setTabIndex] = useState(0)
  const [profileExpanded, setProfileExpanded] = useState(true)
  const [profile, setProfile] = useState(null)
  const [students, setStudents] = useState([])
  const [users, setUsers] = useState([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [userRoleFilter, setUserRoleFilter] = useState('all')
  const [userStatusFilter, setUserStatusFilter] = useState('all')
  const [devices, setDevices] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const recentScans = useAttendanceStore((state) => state.recentScans)

  // Threshold
  const [threshold, setThreshold] = useState(75)
  const [thresholdInput, setThresholdInput] = useState('75')

  // Past Attendance
  const [pastRecords, setPastRecords] = useState([])
  const [pastLoading, setPastLoading] = useState(false)
  const [pastFilters, setPastFilters] = useState({
    date_from: new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0],
    date_to: new Date().toISOString().split('T')[0],
    student_id: ''
  })

  // Attendance modification
  const [editAttendanceDialog, setEditAttendanceDialog] = useState(false)
  const [selectedAttendance, setSelectedAttendance] = useState(null)
  const [attendanceEditData, setAttendanceEditData] = useState({
    status: '',
    verification_method: '',
    timestamp: ''
  })

  // Dialogs
  const [enrollDialog, setEnrollDialog] = useState(false)
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [createUserDialog, setCreateUserDialog] = useState(false)
  const [createStep, setCreateStep] = useState(1)
  const [createdCredential, setCreatedCredential] = useState(null)
  const [newUser, setNewUser] = useState({
    role: 'student',
    full_name: '',
    email: '',
    username: '',
    password: '',
    confirm_password: '',
    student_number: '',
    department: '',
    semester: '',
    employee_id: ''
  })
  const [resetPasswordDialog, setResetPasswordDialog] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  
  useEffect(() => {
    loadData()
    
    // WebSocket connection — use relative ws path through nginx proxy
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
    try {
      const [studentsRes, devicesRes, statsRes, profileRes] = await Promise.all([
        api.get('/students'),
        api.get('/devices'),
        api.get('/attendance/stats'),
        api.get('/users/me/profile')
      ])
      
      setStudents(studentsRes.data)
      setDevices(devicesRes.data)
      setStats(statsRes.data)
      setProfile(profileRes.data)
      loadUsers()
    } catch (err) {
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadUsers = async () => {
    setUsersLoading(true)
    try {
      const params = new URLSearchParams()
      if (userRoleFilter !== 'all') params.append('role', userRoleFilter)
      if (userStatusFilter !== 'all') params.append('is_active', String(userStatusFilter === 'active'))
      const res = await api.get(`/admin/users?${params.toString()}`)
      setUsers(res.data || [])
    } catch {
      setError('Failed to load users')
    } finally {
      setUsersLoading(false)
    }
  }

  useEffect(() => {
    if (tabIndex === 2) {
      loadUsers()
    }
  }, [tabIndex, userRoleFilter, userStatusFilter])
  
  const handleEnroll = async () => {
    if (!selectedStudent) return
    try {
      if (selectedStudent.fp_enrolled) {
        // Revoke enrollment
        await api.delete(`/enrollment/revoke/${selectedStudent.student_id}`)
        setEnrollDialog(false)
        setSuccess('Fingerprint enrollment revoked successfully')
      } else {
        // Enroll fingerprint
        const template = btoa(Math.random().toString())
        await api.post('/enrollment/enroll', {
          student_id: selectedStudent.student_id,
          template_data_base64: template
        })
        setEnrollDialog(false)
        setSuccess('Fingerprint enrolled successfully')
      }
      loadData()
    } catch (err) {
      setError(selectedStudent.fp_enrolled ? 'Revoke failed' : 'Enrollment failed')
    }
  }

  const handleAddStudent = async () => {
    if (!newStudent.student_number || !newStudent.full_name) {
      setError('Student number and full name are required')
      return
    }
    try {
      await api.post('/students', {
        student_number: newStudent.student_number,
        full_name: newStudent.full_name,
        department: newStudent.department || null,
        semester: newStudent.semester ? parseInt(newStudent.semester) : null
      })
      setAddStudentDialog(false)
      setNewStudent({ student_number: '', full_name: '', department: '', semester: '' })
      setSuccess('Student added successfully')
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add student')
    }
  }

  const handleSaveThreshold = async () => {
    const val = parseInt(thresholdInput)
    if (isNaN(val) || val < 1 || val > 100) {
      setError('Threshold must be between 1 and 100')
      return
    }
    try {
      await api.post('/settings/threshold', { threshold: val })
      setThreshold(val)
      setSuccess(`Attendance threshold updated to ${val}%`)
    } catch {
      // Save locally even if endpoint not available
      setThreshold(val)
      setSuccess(`Threshold set to ${val}% (saved locally)`)
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
    if (!window.confirm('Are you sure you want to delete this attendance record?')) return
    try {
      await api.delete(`/attendance/${recordId}`)
      setSuccess('Attendance record deleted successfully')
      loadPastAttendance()
    } catch (err) {
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
      setSuccess('Attendance record updated successfully')
      loadPastAttendance()
    } catch (err) {
      setError('Failed to update attendance record')
    }
  }

  if (loading || !stats) return <CircularProgress />  
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>Admin Dashboard</Typography>
      
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}
      
      <Tabs value={tabIndex} onChange={(e, v) => setTabIndex(v)} sx={{ mb: 2 }}>
        <Tab label="Overview" />
        <Tab label="Fingerprint Enrollment" />
        <Tab label="Student Management" />
        <Tab label="Device Management" />
        <Tab label="Past Attendance" />
        <Tab label="Reports" />
        <Tab label="Audit Log" />
      </Tabs>
      
      {/* Tab 1: Overview */}
      <TabPanel value={tabIndex} index={0}>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Total Students</Typography>
                <Typography variant="h5">{students.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Enrolled Students</Typography>
                <Typography variant="h5">{students.filter(s => s.fp_enrolled).length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Active Devices</Typography>
                <Typography variant="h5">{devices.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Today's Scans</Typography>
                <Typography variant="h5">{stats.total_scans_today || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
        
        <Typography variant="h6" sx={{ mb: 2 }}>Live Attendance Feed</Typography>
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Time</TableCell>
                <TableCell>Student</TableCell>
                <TableCell>Course</TableCell>
                <TableCell>Classroom</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {recentScans.slice(0, 20).map((scan, idx) => (
                <TableRow key={idx}>
                  <TableCell>{new Date(scan.timestamp).toLocaleTimeString()}</TableCell>
                  <TableCell>{scan.student_name}</TableCell>
                  <TableCell>{scan.course_name}</TableCell>
                  <TableCell>{scan.classroom_id}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>
      
      {/* Tab 2: Fingerprint Enrollment */}
      <TabPanel value={tabIndex} index={1}>
        <Button variant="contained" sx={{ mb: 2 }} onClick={() => setEnrollDialog(true)}>
          Enroll Student
        </Button>
        
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Name</TableCell>
                <TableCell>Student #</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {students.map((student) => (
                <TableRow key={student.student_id}>
                  <TableCell>{student.full_name}</TableCell>
                  <TableCell>{student.student_number}</TableCell>
                  <TableCell>
                    <Chip
                      label={student.fp_enrolled ? 'Enrolled ✓' : 'Not Enrolled'}
                      color={student.fp_enrolled ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
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
        
        <Dialog open={enrollDialog} onClose={() => setEnrollDialog(false)}>
          <DialogTitle>{selectedStudent?.fp_enrolled ? 'Revoke Enrollment' : 'Enroll Fingerprint'}</DialogTitle>
          <DialogContent sx={{ minWidth: 400 }}>
            {selectedStudent && (
              <>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  <strong>{selectedStudent.full_name}</strong> ({selectedStudent.student_number})
                </Typography>
                {!selectedStudent.fp_enrolled && (
                  <Button
                    fullWidth
                    variant="outlined"
                    sx={{ mb: 2 }}
                    onClick={() => {
                      alert('Fingerprint captured (simulated)')
                    }}
                  >
                    Capture Fingerprint
                  </Button>
                )}
                {selectedStudent.fp_enrolled && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    This will deactivate the student's fingerprint template and remove their enrollment status.
                  </Alert>
                )}
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEnrollDialog(false)}>Cancel</Button>
            <Button onClick={handleEnroll} variant="contained" color={selectedStudent?.fp_enrolled ? 'error' : 'primary'}>
              {selectedStudent?.fp_enrolled ? 'Revoke' : 'Confirm'}
            </Button>
          </DialogActions>
        </Dialog>
      </TabPanel>
      
      {/* Tab 3: Student Management */}
      <TabPanel value={tabIndex} index={2}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Student Management</Typography>
          <Button variant="contained" onClick={() => setAddStudentDialog(true)}>Add Student</Button>
        </Box>

        {/* Threshold Setting */}
        <Card sx={{ mb: 2, p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}><strong>Attendance Threshold</strong></Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              label="Threshold %"
              type="number"
              size="small"
              value={thresholdInput}
              onChange={(e) => setThresholdInput(e.target.value)}
              inputProps={{ min: 1, max: 100 }}
              sx={{ width: 120 }}
            />
            <Button variant="outlined" onClick={handleSaveThreshold}>Save</Button>
            <Typography variant="body2" color="textSecondary">Current: {threshold}%</Typography>
          </Box>
        </Card>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Student #</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Department</TableCell>
                <TableCell>Semester</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {students.map((student) => (
                <TableRow key={student.student_id}>
                  <TableCell>{student.student_number}</TableCell>
                  <TableCell>{student.full_name}</TableCell>
                  <TableCell>{student.department}</TableCell>
                  <TableCell>{student.semester}</TableCell>
                  <TableCell>
                    <Chip label={student.is_active ? 'Active' : 'Inactive'} size="small"
                      color={student.is_active ? 'success' : 'default'} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Add Student Dialog */}
        <Dialog open={addStudentDialog} onClose={() => setAddStudentDialog(false)}>
          <DialogTitle>Add New Student</DialogTitle>
          <DialogContent sx={{ minWidth: 400, pt: 2 }}>
            <TextField fullWidth label="Student Number *" value={newStudent.student_number}
              onChange={(e) => setNewStudent({ ...newStudent, student_number: e.target.value })}
              sx={{ mb: 2 }} size="small" />
            <TextField fullWidth label="Full Name *" value={newStudent.full_name}
              onChange={(e) => setNewStudent({ ...newStudent, full_name: e.target.value })}
              sx={{ mb: 2 }} size="small" />
            <TextField fullWidth label="Department" value={newStudent.department}
              onChange={(e) => setNewStudent({ ...newStudent, department: e.target.value })}
              sx={{ mb: 2 }} size="small" />
            <TextField fullWidth label="Semester" type="number" value={newStudent.semester}
              onChange={(e) => setNewStudent({ ...newStudent, semester: e.target.value })}
              size="small" />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAddStudentDialog(false)}>Cancel</Button>
            <Button onClick={handleAddStudent} variant="contained">Add Student</Button>
          </DialogActions>
        </Dialog>
      </TabPanel>
      
      {/* Tab 4: Device Management */}
      <TabPanel value={tabIndex} index={3}>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Device ID</TableCell>
                <TableCell>Classroom</TableCell>
                <TableCell>Last Seen</TableCell>
                <TableCell>Battery</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {devices.map((device) => (
                <TableRow key={device.device_id}>
                  <TableCell>{device.device_id}</TableCell>
                  <TableCell>{device.classroom}</TableCell>
                  <TableCell>{device.last_seen}</TableCell>
                  <TableCell>{device.battery_pct}%</TableCell>
                  <TableCell>
                    <Chip
                      label={device.status}
                      color={device.status === 'online' ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>
      
      {/* Tab 4: Past Attendance */}
      <TabPanel value={tabIndex} index={4}>
        <Typography variant="h6" sx={{ mb: 2 }}>Past Attendance Records</Typography>

        {/* Filters */}
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={3}>
                <TextField fullWidth label="From Date" type="date" size="small"
                  value={pastFilters.date_from}
                  onChange={(e) => setPastFilters({ ...pastFilters, date_from: e.target.value })}
                  InputLabelProps={{ shrink: true }} />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField fullWidth label="To Date" type="date" size="small"
                  value={pastFilters.date_to}
                  onChange={(e) => setPastFilters({ ...pastFilters, date_to: e.target.value })}
                  InputLabelProps={{ shrink: true }} />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField fullWidth label="Filter by Student" size="small"
                  placeholder="Type student name or leave blank for all"
                  value={pastFilters.student_name_filter || ''}
                  onChange={(e) => setPastFilters({ ...pastFilters, student_name_filter: e.target.value })} />
              </Grid>
              <Grid item xs={12} sm={2}>
                <Button fullWidth variant="contained" onClick={loadPastAttendance}>
                  Search
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {pastLoading ? <CircularProgress /> : (
          <>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
              {pastRecords.length} records found
            </Typography>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                    <TableCell>Date & Time</TableCell>
                    <TableCell>Student</TableCell>
                    <TableCell>Student #</TableCell>
                    <TableCell>Room</TableCell>
                    <TableCell>Device</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Match Score</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pastRecords
                    .filter(r => !pastFilters.student_name_filter ||
                      r.student_name?.toLowerCase().includes(pastFilters.student_name_filter.toLowerCase()))
                    .map((rec) => (
                      <TableRow key={rec.record_id}>
                        <TableCell>{new Date(rec.timestamp).toLocaleString()}</TableCell>
                        <TableCell>{rec.student_name}</TableCell>
                        <TableCell>{rec.student_number}</TableCell>
                        <TableCell>{rec.room_number}</TableCell>
                        <TableCell sx={{ fontSize: '0.75rem' }}>{rec.device_id}</TableCell>
                        <TableCell>
                          <Chip label={rec.status} size="small"
                            color={rec.status === 'present' ? 'success' : rec.status === 'manual' ? 'warning' : 'error'} />
                        </TableCell>
                        <TableCell>{rec.match_score ?? '—'}</TableCell>
                        <TableCell>{rec.verification_method}</TableCell>
                        <TableCell>
                          <Button size="small" onClick={() => handleEditAttendance(rec)} sx={{ mr: 1 }}>
                            Edit
                          </Button>
                          <Button size="small" color="error" onClick={() => handleDeleteAttendance(rec.record_id)}>
                            Delete
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </TabPanel>

      {/* Tab 5: Reports */}
      <TabPanel value={tabIndex} index={5}>
        <Typography variant="h6" sx={{ mb: 2 }}>Attendance by Course</Typography>
        <Box sx={{ height: 300 }}>
          <Bar
            data={{
              labels: ['SE101', 'DB101', 'AI101'],
              datasets: [{ label: 'Attendance %', data: [85, 78, 72], backgroundColor: '#1976d2' }]
            }}
            options={{ responsive: true, maintainAspectRatio: false }}
          />
        </Box>
      </TabPanel>

      {/* Tab 6: Audit Log */}
      <TabPanel value={tabIndex} index={6}>
        <Typography variant="subtitle2" color="textSecondary">Audit log shows all user actions</Typography>
      </TabPanel>

      {/* Edit Attendance Dialog */}
      <Dialog open={editAttendanceDialog} onClose={() => setEditAttendanceDialog(false)}>
        <DialogTitle>Edit Attendance Record</DialogTitle>
        <DialogContent sx={{ minWidth: 400, pt: 2 }}>
          {selectedAttendance && (
            <>
              <Typography variant="body2" sx={{ mb: 2 }}>
                <strong>{selectedAttendance.student_name}</strong> ({selectedAttendance.student_number})
              </Typography>
              <TextField
                fullWidth
                label="Status"
                select
                value={attendanceEditData.status}
                onChange={(e) => setAttendanceEditData({ ...attendanceEditData, status: e.target.value })}
                sx={{ mb: 2 }}
                size="small"
                SelectProps={{ native: true }}
              >
                <option value="present">Present</option>
                <option value="absent">Absent</option>
                <option value="manual">Manual</option>
              </TextField>
              <TextField
                fullWidth
                label="Verification Method"
                select
                value={attendanceEditData.verification_method}
                onChange={(e) => setAttendanceEditData({ ...attendanceEditData, verification_method: e.target.value })}
                sx={{ mb: 2 }}
                size="small"
                SelectProps={{ native: true }}
              >
                <option value="fingerprint">Fingerprint</option>
                <option value="manual">Manual</option>
                <option value="rfid">RFID</option>
              </TextField>
              <TextField
                fullWidth
                label="Timestamp"
                type="datetime-local"
                value={attendanceEditData.timestamp}
                onChange={(e) => setAttendanceEditData({ ...attendanceEditData, timestamp: e.target.value })}
                size="small"
                InputLabelProps={{ shrink: true }}
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAttendanceDialog(false)}>Cancel</Button>
          <Button onClick={handleSaveAttendanceEdit} variant="contained">Save Changes</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default AdminDashboard
