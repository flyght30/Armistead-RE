import React from 'react';
import { Settings as SettingsIcon, User, Bell, Shield, Palette } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';

export default function Settings() {
  const settingsSections = [
    {
      icon: User,
      title: 'Profile',
      description: 'Manage your account information and preferences.',
      color: 'text-blue-600 bg-blue-50',
    },
    {
      icon: Bell,
      title: 'Notifications',
      description: 'Configure email and in-app notification settings.',
      color: 'text-yellow-600 bg-yellow-50',
    },
    {
      icon: Shield,
      title: 'Security',
      description: 'Password, two-factor authentication, and login sessions.',
      color: 'text-red-600 bg-red-50',
    },
    {
      icon: Palette,
      title: 'Appearance',
      description: 'Theme preferences and display settings.',
      color: 'text-purple-600 bg-purple-50',
    },
  ];

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Manage your account and preferences"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {settingsSections.map((section) => (
          <Card key={section.title} className="hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-start gap-4">
              <div className={`rounded-lg p-3 ${section.color}`}>
                <section.icon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{section.title}</h3>
                <p className="text-sm text-gray-500 mt-1">{section.description}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card title="About" subtitle="Application information">
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Application</span>
            <span className="text-gray-900 font-medium">Armistead RE Transaction Manager</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Version</span>
            <span className="text-gray-900 font-medium">1.0.0-beta</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Environment</span>
            <span className="text-gray-900 font-medium">Development</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">API Endpoint</span>
            <span className="text-gray-900 font-medium text-xs">{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
