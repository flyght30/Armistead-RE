import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import NewTransaction from './pages/NewTransaction';
import TransactionDetail from './pages/TransactionDetail';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewTransaction />} />
        <Route path="/transaction/:id" element={<TransactionDetail />} />
      </Routes>
    </Router>
  );
};

export default App;
