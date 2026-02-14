import React from 'react';
import { Check, Clock, AlertCircle } from 'lucide-react';

export interface TimelineItem {
  id: string;
  title: string;
  subtitle?: string;
  date?: string;
  status: 'completed' | 'in_progress' | 'pending' | 'overdue' | 'not_started';
  description?: string;
}

interface TimelineProps {
  items: TimelineItem[];
}

const statusConfig: Record<string, { dot: string; icon: React.ReactNode; line: string }> = {
  completed: {
    dot: 'bg-green-500',
    icon: <Check className="w-3 h-3 text-white" />,
    line: 'bg-green-300',
  },
  in_progress: {
    dot: 'bg-blue-500',
    icon: <Clock className="w-3 h-3 text-white" />,
    line: 'bg-blue-300',
  },
  pending: {
    dot: 'bg-gray-300',
    icon: null,
    line: 'bg-gray-200',
  },
  not_started: {
    dot: 'bg-gray-300',
    icon: null,
    line: 'bg-gray-200',
  },
  overdue: {
    dot: 'bg-red-500',
    icon: <AlertCircle className="w-3 h-3 text-white" />,
    line: 'bg-red-300',
  },
};

export default function Timeline({ items }: TimelineProps) {
  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {items.map((item, idx) => {
          const config = statusConfig[item.status] || statusConfig.pending;
          const isLast = idx === items.length - 1;

          return (
            <li key={item.id}>
              <div className="relative pb-8">
                {!isLast && (
                  <span
                    className={`absolute left-3 top-6 -ml-px h-full w-0.5 ${config.line}`}
                    aria-hidden="true"
                  />
                )}
                <div className="relative flex items-start gap-4">
                  <div
                    className={`relative flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full ${config.dot}`}
                  >
                    {config.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900">{item.title}</p>
                      {item.date && (
                        <time className="text-xs text-gray-500 whitespace-nowrap ml-2">{item.date}</time>
                      )}
                    </div>
                    {item.subtitle && (
                      <p className="text-xs text-gray-500 mt-0.5">{item.subtitle}</p>
                    )}
                    {item.description && (
                      <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                    )}
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
