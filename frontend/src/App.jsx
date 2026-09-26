import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Shell from './components/Shell'
import Dashboard from './pages/Dashboard'
import NewTender from './pages/NewTender'
import TenderDetail from './pages/TenderDetail'
import BidDetail from './pages/BidDetail'
import AdminUsers from './pages/AdminUsers'
import ReviewQueue from './pages/ReviewQueue'
import Notifications from './pages/Notifications'

function Private({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return children
}

function Routed() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Private>
            <Shell />
          </Private>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="tenders/new" element={<NewTender />} />
        <Route path="tenders/:tenderId" element={<TenderDetail />} />
        <Route path="tenders/:tenderId/bids/:bidId" element={<BidDetail />} />
        <Route path="admin/users" element={<AdminUsers />} />
        <Route path="reviews/queue" element={<ReviewQueue />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routed />
      </BrowserRouter>
    </AuthProvider>
  )
}
