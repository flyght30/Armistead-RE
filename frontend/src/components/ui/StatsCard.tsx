import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  icon: LucideIcon;
  label: string;
  value: number | string;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'indigo';
}

const colorStyles: Record<string, { bg: string; icon: string }> = {
  blue: { bg: 'bg-blue-50', icon: 'text-blue-600' },
  green: { bg: 'bg-green-50', icon: 'text-green-600' },
  yellow: { bg: 'bg-yellow-50', icon: 'text-yellow-600' },
  red: { bg: 'bg-red-50', icon: 'text-red-600' },
  purple: { bg: 'bg-purple-50', icon: 'text-purple-600' },
  indigo: { bg: 'bg-indigo-50', icon: 'text-indigo-600' },
};

export default function StatsCard({ icon: Icon, label, value, color = 'blue' }: StatsCardProps) {
  const style = colorStyles[color] || colorStyles.blue;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center gap-4 hover:shadow-md transition-shadow">
      <div className={`${style.bg} rounded-lg p-3`}>
        <Icon className={`w-6 h-6 ${style.icon}`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}
