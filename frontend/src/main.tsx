import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClerkProvider } from '@clerk/clerk-react';
import App from './App';
import './index.css';

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function AppWithProviders() {
  const inner = (
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );

  // Only wrap with Clerk if a real publishable key is provided
  if (CLERK_PUBLISHABLE_KEY && CLERK_PUBLISHABLE_KEY !== 'your_clerk_publishable_key') {
    return (
      <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
        {inner}
      </ClerkProvider>
    );
  }

  return inner;
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AppWithProviders />
  </React.StrictMode>,
);
