import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/react'
import { useAuthStore } from '@/stores/authStore'
import Layout from '@/components/Layout'
import LoginForm from '@/components/LoginForm'
import PipelineBoard from '@/components/PipelineBoard'
import ReviewPanel from '@/components/ReviewPanel'
import ArchiveBrowser from '@/components/ArchiveBrowser'
import AuditChain from '@/components/AuditChain'
import MetricsDashboard from '@/components/MetricsDashboard'
import ErrorBoundary from '@/components/ErrorBoundary'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  const { isAuthenticated, fetchProfile } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) {
      void fetchProfile()
    }
  }, [isAuthenticated, fetchProfile])

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginForm />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<PipelineBoard />} />
                  <Route path="/review" element={<ReviewPanel />} />
                  <Route path="/archive" element={<ArchiveBrowser />} />
                  <Route path="/audit/:docId" element={<AuditChain />} />
                  <Route path="/metrics" element={<MetricsDashboard />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
      <Analytics />
      <SpeedInsights />
    </ErrorBoundary>
  )
}
