import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewApplication from './pages/NewApplication';
import MyCases from './pages/MyCases';
import AllRuns from './pages/AllRuns';
import Results from './pages/Results';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/new-application" replace />} />
        <Route path="/new-application" element={<NewApplication />} />
        <Route path="/my-cases" element={<MyCases />} />
        <Route path="/all-runs" element={<AllRuns />} />
        <Route path="/results/:runId?" element={<Results />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Layout>
  );
}

export default App;
