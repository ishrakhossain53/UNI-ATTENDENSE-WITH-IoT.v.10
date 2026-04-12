import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  token: localStorage.getItem('auth_token'),
  user: JSON.parse(localStorage.getItem('auth_user') || 'null'),
  isLoading: false,
  
  login: (token, user) => {
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_user', JSON.stringify(user))
    set({ token, user, isLoading: false })
  },
  
  logout: () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    set({ token: null, user: null })
  },
  
  setLoading: (isLoading) => set({ isLoading }),
  
  initializeFromStorage: () => {
    const token = localStorage.getItem('auth_token')
    const user = JSON.parse(localStorage.getItem('auth_user') || 'null')
    set({ token, user })
  }
}))

export const useAttendanceStore = create((set) => ({
  recentScans: [],
  
  addScan: (scan) => set((state) => ({
    recentScans: [scan, ...state.recentScans].slice(0, 50)
  })),
  
  clearScans: () => set({ recentScans: [] })
}))
