import React, { type ReactNode, useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useClerk, useUser } from '@clerk/clerk-react';
import {
  CalendarCheck,
  LayoutDashboard,
  Plus,
  Users,
  Settings,
  LogOut,
  Building2,
  Menu,
  X,
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { to: '/', label: 'Today', icon: CalendarCheck },
  { to: '/pipeline', label: 'Pipeline', icon: LayoutDashboard },
  { to: '/new', label: 'New Transaction', icon: Plus },
  { to: '/parties', label: 'Parties', icon: Users },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="mt-6 flex-1">
      <ul className="space-y-1 px-3">
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/**
 * Inner footer that uses Clerk hooks.
 * Only rendered when ClerkProvider is present.
 */
const AuthFooter: React.FC = () => {
  const { signOut } = useClerk();
  const { user } = useUser();

  return (
    <div className="px-3 pb-4 border-t border-gray-700 pt-4">
      {user && (
        <div className="flex items-center gap-3 mb-3 px-3">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">
            {user.fullName?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user.fullName}</p>
            <p className="text-xs text-gray-400 truncate">
              {user.primaryEmailAddress?.emailAddress}
            </p>
          </div>
        </div>
      )}
      <button
        onClick={() => signOut()}
        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-700 transition-colors w-full"
      >
        <LogOut className="w-4 h-4" />
        Sign Out
      </button>
    </div>
  );
};

/**
 * Fallback when Clerk is not configured.
 */
const NoAuthFooter: React.FC = () => {
  return (
    <div className="px-3 pb-4 border-t border-gray-700 pt-4">
      <div className="flex items-center gap-3 px-3">
        <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-gray-300 text-xs font-bold">
          D
        </div>
        <div>
          <p className="text-sm font-medium text-gray-300">Dev Mode</p>
          <p className="text-xs text-gray-500">No auth configured</p>
        </div>
      </div>
    </div>
  );
};

/**
 * Error boundary to catch Clerk hooks failing when provider is absent.
 */
class ClerkErrorBoundary extends React.Component<
  { fallback: React.ReactNode; children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { fallback: React.ReactNode; children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

/** Shared sidebar content used by both desktop and mobile */
function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      {/* Logo */}
      <div className="px-6 py-5 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
          <Building2 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-bold text-white">Armistead RE</h1>
          <p className="text-xs text-gray-400">Transaction Manager</p>
        </div>
      </div>

      {/* Navigation */}
      <SidebarNav onNavigate={onNavigate} />

      {/* Footer */}
      <ClerkErrorBoundary fallback={<NoAuthFooter />}>
        <AuthFooter />
      </ClerkErrorBoundary>
    </>
  );
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Auto-close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location]);

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Desktop sidebar: always visible at md+ */}
      <aside className="hidden md:flex w-64 bg-gray-900 text-white flex-col flex-shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Mobile sidebar drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 text-white flex flex-col transform transition-transform duration-200 ease-in-out md:hidden ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Close button inside mobile sidebar */}
        <div className="absolute top-4 right-3">
          <button
            onClick={closeSidebar}
            className="p-1 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <SidebarContent onNavigate={closeSidebar} />
      </aside>

      {/* Main content column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-900">Armistead RE</span>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
