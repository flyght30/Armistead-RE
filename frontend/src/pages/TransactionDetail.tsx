import React from 'react';
import apiClient from '../lib/api';
import { useQuery } from '@tanstack/react-query';
import { Transaction, Party } from '../types/transaction';

const fetchTransaction = async (id: string) => {
  const response = await apiClient.get<Transaction>(`/transactions/${id}`);
  return response.data;
};

const TransactionDetail: React.FC<{ id: string }> = ({ id }) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['transaction', id],
    queryFn: () => fetchTransaction(id),
  });

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error fetching transaction</div>;

  return (
    <div>
      <h1>{data.title}</h1>
      <p>Status: {data.status}</p>
      <h2>Parties:</h2>
      <ul>
        {data.parties.map((party) => (
          <li key={party.id}>
            {party.name} - {party.role}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TransactionDetail;
