import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import NewApplication from './pages/NewApplication';
import MyCases from './pages/MyCases';
import AllRuns from './pages/AllRuns';
import Results from './pages/Results';
import ApplicationDetails from './pages/ApplicationDetails';
import HILReview from './pages/HILReview';
import { skipToMainContent } from './utils/accessibility';
import './styles/accessibility.css';

function App() {
  return (
    <>
      <a
        href="#main-content"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          skipToMainContent('main-content');
        }}
      >
        Skip to main content
      </a>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected Routes with Layout */}
        <Route path="/" element={<Navigate to="/new-application" replace />} />
        <Route
          path="/new-application"
          element={
            <ProtectedRoute>
              <Layout>
                <NewApplication />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-cases"
          element={
            <ProtectedRoute>
              <Layout>
                <MyCases />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:applicationId"
          element={
            <ProtectedRoute>
              <Layout>
                <ApplicationDetails />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:applicationId/runs/:runId"
          element={
            <ProtectedRoute>
              <Layout>
                <Results />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:applicationId/runs/:runId/review"
          element={
            <ProtectedRoute allowedRoles={['officer', 'admin', 'reviewer', 'planner']}>
              <Layout>
                <HILReview />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/all-runs"
          element={
            <ProtectedRoute>
              <Layout>
                <AllRuns />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}

export default App;
