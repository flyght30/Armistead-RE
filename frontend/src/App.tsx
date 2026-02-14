import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './components/ui/ToastContext';
import TodayView from './pages/TodayView';
import Dashboard from './pages/Dashboard';
import NewTransaction from './pages/NewTransaction';
import TransactionDetailPage from './pages/TransactionDetail';
import Parties from './pages/Parties';
import Settings from './pages/Settings';

const App: React.FC = () => {
  return (
    <Router>
      <ToastProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<TodayView />} />
            <Route path="/pipeline" element={<Dashboard />} />
            <Route path="/new" element={<NewTransaction />} />
            <Route path="/transaction/:id" element={<TransactionDetailPage />} />
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
