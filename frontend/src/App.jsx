import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Patients from './pages/Patients';
import Admissions from './pages/Admissions';
import Beds from './pages/Beds';
import Pharmacy from './pages/Pharmacy';
import Billing from './pages/Billing';
import Lab from './pages/Lab';
import Appointments from './pages/Appointments';
import Admin from './pages/Admin';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
        
        {/* Protected Routes Wrapper */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            
            {/* Actual routes */}
            <Route path="/patients" element={<Patients />} />
            <Route path="/admissions" element={<Admissions />} />
            <Route path="/beds" element={<Beds />} />
            <Route path="/pharmacy" element={<Pharmacy />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/lab" element={<Lab />} />
            <Route path="/appointments" element={<Appointments />} />
            
            <Route element={<ProtectedRoute allowedRoles={['super_admin']} />}>
              <Route path="/admin" element={<Admin />} />
            </Route>
          </Route>
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;
