import React from 'react';

interface HealthBadgeProps {
  score: number | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  className?: string;
}

function getColor(score: number): { bg: string; text: string; dot: string; label: string } {
  if (score <= 40) return { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500', label: 'At Risk' };
  if (score <= 70) return { bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500', label: 'Needs Attention' };
  return { bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500', label: 'On Track' };
}

const sizeMap = {
  sm: { badge: 'w-6 h-6 text-xs', dot: 'w-2 h-2' },
  md: { badge: 'w-8 h-8 text-sm', dot: 'w-3 h-3' },
  lg: { badge: 'w-10 h-10 text-base', dot: 'w-4 h-4' },
};

export default function HealthBadge({ score, size = 'md', showScore = true, className = '' }: HealthBadgeProps) {
  if (score == null) {
    return (
      <span className={`inline-flex items-center justify-center rounded-full bg-gray-100 ${sizeMap[size].badge} ${className}`}>
        <span className={`rounded-full bg-gray-400 ${sizeMap[size].dot}`} />
      </span>
    );
  }

  const colors = getColor(score);

  if (!showScore) {
    return (
      <span className={`inline-flex items-center justify-center rounded-full ${className}`} title={`Health: ${Math.round(score)} — ${colors.label}`}>
        <span className={`rounded-full ${colors.dot} ${sizeMap[size].dot} ${score <= 40 ? 'animate-pulse' : ''}`} />
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-semibold ${colors.bg} ${colors.text} ${sizeMap[size].badge} ${className}`}
      title={`Health: ${Math.round(score)} — ${colors.label}`}
    >
      {Math.round(score)}
    </span>
  );
}

export function HealthDot({ score, className = '' }: { score: number | null | undefined; className?: string }) {
  if (score == null) {
    return <span className={`inline-block w-2.5 h-2.5 rounded-full bg-gray-300 ${className}`} />;
  }
  const colors = getColor(score);
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${colors.dot} ${score <= 40 ? 'animate-pulse' : ''} ${className}`}
      title={`Health: ${Math.round(score)}`}
    />
  );
}
