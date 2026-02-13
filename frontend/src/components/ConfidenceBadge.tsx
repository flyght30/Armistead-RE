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
