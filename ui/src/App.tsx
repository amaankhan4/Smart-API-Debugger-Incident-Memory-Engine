import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from 'layouts/AppLayout';
import { DashboardPage } from 'pages/DashboardPage';
import { UploadPage } from 'pages/UploadPage';
import { LogExplorerPage } from 'pages/LogExplorerPage';
import { IncidentsPage } from 'pages/IncidentsPage';
import { IncidentDetailPage } from 'pages/IncidentDetailPage';

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/logs" element={<LogExplorerPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
