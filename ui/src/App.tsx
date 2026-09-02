import { Navigate, Route, Routes } from 'react-router-dom';

import { ProtectedRoute, PublicOnlyRoute } from 'components/ProtectedRoute';
import { AppLayout } from 'layouts/AppLayout';
import { AnalyticsPage } from 'pages/AnalyticsPage';
import { FilesPage } from 'pages/FilesPage';
import { IncidentDetailPage } from 'pages/IncidentDetailPage';
import { IncidentsPage } from 'pages/IncidentsPage';
import { LogExplorerPage } from 'pages/LogExplorerPage';
import { LoginPage } from 'pages/LoginPage';
import { OverviewPage } from 'pages/OverviewPage';
import { RegisterPage } from 'pages/RegisterPage';
import { SearchPage } from 'pages/SearchPage';

export default function App() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/files" element={<FilesPage />} />
          <Route path="/logs" element={<LogExplorerPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/overview" replace />} />
      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  );
}

