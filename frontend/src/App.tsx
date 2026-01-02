import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewApplication from './pages/NewApplication';
import MyCases from './pages/MyCases';
import AllRuns from './pages/AllRuns';
import Results from './pages/Results';
import ApplicationDetails from './pages/ApplicationDetails';
import HILReview from './pages/HILReview';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/new-application" replace />} />
        <Route path="/new-application" element={<NewApplication />} />
        <Route path="/my-cases" element={<MyCases />} />
        <Route path="/applications/:applicationId" element={<ApplicationDetails />} />
        <Route path="/applications/:applicationId/runs/:runId" element={<Results />} />
        <Route path="/applications/:applicationId/runs/:runId/review" element={<HILReview />} />
        <Route path="/all-runs" element={<AllRuns />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Layout>
  );
}

export default App;
