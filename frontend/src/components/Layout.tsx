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
