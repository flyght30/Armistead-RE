# Phase 1 — Step 1.5: Frontend scaffolding & dashboard
**Generated:** 2026-02-13T13:05:53.218950

===FILE: frontend/package.json===
```json
{
  "name": "armistead-re",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@clerk/clerk-react": "^3.0.0",
    "@tanstack/react-query": "^4.0.0",
    "axios": "^1.0.0",
    "lucide-react": "^0.25.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "react-router-dom": "^6.0.0",
    "tailwindcss": "^3.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "typescript": "^4.5.0"
  }
}
===END FILE===

===FILE: frontend/tsconfig.json===
```json
{
  "compilerOptions": {
    "target": "esnext",
    "lib": ["dom", "es2015"],
    "jsx": "react-jsx",
    "module": "esnext",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist"
  },
  "include": ["src"]
}
===END FILE===

===FILE: frontend/tailwind.config.js===
```js
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
===END FILE===

===FILE: frontend/src/main.tsx===
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClerkProvider } from '@clerk/clerk-react';
import App from './App';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ClerkProvider frontendApi="your-clerk-frontend-api">
        <App />
      </ClerkProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
===END FILE===

===FILE: frontend/src/App.tsx===
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
===END FILE===

===FILE: frontend/src/lib/api.ts===
import axios from 'axios';
import { clerkClient } from '@clerk/clerk-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use(async (config) => {
  const session = await clerkClient.session.getActive();
  if (session) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
}, (error) => Promise.reject(error));

export default apiClient;
===END FILE===

===FILE: frontend/src/types/transaction.ts===
import { z } from 'zod';

export const TransactionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  file_path: z.string(),
  created_by_id: z.string(),
});

export type Transaction = z.infer<typeof TransactionSchema>;
===END FILE===

===FILE: frontend/src/types/party.ts===
import { z } from 'zod';

export const PartySchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string(),
  contact_info: z.record(z.string()),
});

export type Party = z.infer<typeof PartySchema>;
===END FILE===

===FILE: frontend/src/stores/transactionStore.ts===
import create from 'zustand';
import { Transaction } from '../types/transaction';

interface TransactionState {
  transactions: Transaction[];
  setTransactions: (transactions: Transaction[]) => void;
}

const useTransactionStore = create<TransactionState>((set) => ({
  transactions: [],
  setTransactions: (transactions) => set({ transactions }),
}));

export default useTransactionStore;
===END FILE===

===FILE: frontend/src/pages/Dashboard.tsx===
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
===END FILE===

===FILE: frontend/src/pages/NewTransaction.tsx===
import React, { useState } from 'react';
import apiClient from '../lib/api';
import FileUpload from '../components/FileUpload';

const NewTransaction: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setFile(event.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;

    setUploading(true);
    try {
      await apiClient.post('/transactions', { file });
      alert('Transaction created successfully');
    } catch (error) {
      console.error(error);
      alert('Error creating transaction');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h1>New Transaction</h1>
      <FileUpload onChange={handleFileChange} />
      {file && <p>Selected file: {file.name}</p>}
      <button onClick={handleSubmit} disabled={uploading}>
        {uploading ? 'Uploading...' : 'Create Transaction'}
      </button>
    </div>
  );
};

export default NewTransaction;
===END FILE===

===FILE: frontend/src/pages/TransactionDetail.tsx===
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
===END FILE===

===FILE: frontend/src/components/FileUpload.tsx===
import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';

const FileUpload: React.FC<{ onChange: (file: File) => void }> = ({ onChange }) => {
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(acceptedFiles);
    onChange(acceptedFiles[0]);
  }, [onChange]);

  const {getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div {...getRootProps()} className="border-dashed border-2 p-4">
      <input {...getInputProps()} />
      {
        isDragActive ?
          <p>Drop the files here ...</p> :
          <p>Drag 'n' drop some files here, or click to select files</p>
      }
    </div>
  );
};

export default FileUpload;
===END FILE===

===FILE: frontend/src/components/PartyCard.tsx===
import React from 'react';
import { Party } from '../types/party';

const PartyCard: React.FC<{ party: Party }> = ({ party }) => {
  return (
    <div className="border p-4 mb-2">
      <h3>{party.name}</h3>
      <p>Role: {party.role}</p>
      <pre>Contact Info: {JSON.stringify(party.contact_info, null, 2)}</pre>
    </div>
  );
};

export default PartyCard;
===END FILE===

===FILE: frontend/src/components/ConfidenceBadge.tsx===
import React from 'react';

interface ConfidenceBadgeProps {
  score: number;
}

const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score }) => {
  let color = '';
  if (score >= 0.9) color = 'bg-green-500';
  else if (score >= 0.7) color = 'bg-yellow-500';
  else color = 'bg-red-500';

  return (
    <span className={`inline-block px-2 py-1 text-white rounded ${color}`}>
      {Math.round(score * 100)}%
    </span>
  );
};

export default ConfidenceBadge;
===END FILE===

===FILE: frontend/src/components/Layout.tsx===
import React from 'react';
import { useClerk } from '@clerk/clerk-react';

const Layout: React.FC = ({ children }) => {
  const { signOut, user } = useClerk();

  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-gray-800 text-white p-4">
        <h1>Armistead RE</h1>
        <nav className="mt-4">
          <ul>
            <li><a href="/">Dashboard</a></li>
            <li><a href="/new">New Transaction</a></li>
          </ul>
        </nav>
        <button onClick={() => signOut()}>Sign Out</button>
      </aside>
      <main className="flex-1 p-4">
        {children}
      </main>
    </div>
  );
};

export default Layout;
===END FILE===
