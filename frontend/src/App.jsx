import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import Register from './pages/Register'
import AdminDashboard from './pages/AdminDashboard'
import AuthCallback from './pages/AuthCallback'


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"               element={<Landing />} />
        <Route path="/signup"         element={<Signup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/auth/callback"  element={<AuthCallback />} />
        <Route path="/register"       element={<Register />} />
        <Route path="/admin"          element={<AdminDashboard />} />
        <Route path="*"               element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}