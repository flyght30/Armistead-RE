import React, { useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './components/ui/ToastContext';
import { setupAuthInterceptor } from './lib/api';
import TodayView from './pages/TodayView';
import Dashboard from './pages/Dashboard';
import NewTransaction from './pages/NewTransaction';
import TransactionDetailPage from './pages/TransactionDetail';
import Parties from './pages/Parties';
import Settings from './pages/Settings';
import AIAdvisor from './pages/AIAdvisor';
import Portal from './pages/Portal';
import Documents from './pages/Documents';
import Commissions from './pages/Commissions';

/**
 * Wires Clerk auth tokens into the API client.
 * Uses Clerk's global window object to fetch session tokens.
 * Silently no-ops when Clerk is not configured.
 */
function AuthInterceptorSetup() {
  const setupDone = useRef(false);

  useEffect(() => {
    if (setupDone.current) return;
    setupDone.current = true;

    setupAuthInterceptor(async () => {
      try {
        const clerk = (window as unknown as { Clerk?: { session?: { getToken: () => Promise<string | null> } } }).Clerk;
        if (clerk?.session) {
          return await clerk.session.getToken();
        }
      } catch {
        // Auth not available
      }
      return null;
    });
  }, []);

  return null;
}

const App: React.FC = () => {
  return (
    <Router>
      <AuthInterceptorSetup />
      <ToastProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<TodayView />} />
            <Route path="/pipeline" element={<Dashboard />} />
            <Route path="/new" element={<NewTransaction />} />
            <Route path="/transaction/:id" element={<TransactionDetailPage />} />
            <Route path="/transaction/:id/advisor" element={<AIAdvisor />} />
            <Route path="/transaction/:id/portal" element={<Portal />} />
            <Route path="/transaction/:id/documents" element={<Documents />} />
            <Route path="/commissions" element={<Commissions />} />
            <Route path="/parties" element={<Parties />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </ToastProvider>
    </Router>
  );
};

export default App;
