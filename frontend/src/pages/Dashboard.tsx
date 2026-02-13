import React from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../lib/api';
import { Transaction } from '../types/transaction';

const fetchTransactions = async () => {
  const response = await apiClient.get<Transaction[]>('/transactions');
  return response.data;
};

const Dashboard: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['transactions'],
    queryFn: fetchTransactions,
  });

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error fetching transactions</div>;

  return (
    <div>
      <h1>Dashboard</h1>
      <ul>
        {data.map((transaction) => (
          <li key={transaction.id}>
            {transaction.title} - {transaction.status}
          </li>
        ))}
      </ul>
      <button onClick={() => navigate('/new')}>New Transaction</button>
    </div>
  );
};

export default Dashboard;
