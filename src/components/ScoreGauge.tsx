import React from 'react';
import clsx from 'clsx';

interface ScoreGaugeProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  showGrade?: boolean;
  grade?: string;
  label?: string;
}

const getScoreColor = (value: number): string => {
  if (value >= 80) return '#1E7F72';  // teal
  if (value >= 60) return '#C99A3A';  // gold
  return '#ef4444';                    // red
};

const getGradeBg = (grade: string): string => {
  if (['A+', 'A', 'A-'].includes(grade)) return 'text-teal-600';
  if (['B+', 'B', 'B-'].includes(grade)) return 'text-gold-500';
  return 'text-red-500';
};

const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  value,
  size = 160,
  strokeWidth = 12,
  showGrade = true,
  grade,
  label = 'Overall Score',
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;
  // We show 270-degree arc (from -225deg to 45deg)
  const arcFraction = 0.75;
  const progress = Math.min(Math.max(value, 0), 100) / 100;
  const dashArray = circumference * arcFraction;
  const dashOffset = dashArray * (1 - progress);
  const color = getScoreColor(value);

  // Extract letter grade (e.g. 'C') and optional qualifier (e.g. 'Requires Improvement')
  const [letterGrade, qualifier] = grade ? grade.split('/').map(s => s.trim()) : ['', ''];

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[135deg]">
          {/* Background track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={strokeWidth}
            strokeDasharray={`${dashArray} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Progress arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${dashArray - dashOffset} ${circumference}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s ease-out' }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center p-2 text-center pointer-events-none">
          <span className="text-3xl font-extrabold font-display leading-none tracking-tight" style={{ color }}>
            {value}
          </span>
          {showGrade && letterGrade && (
            <span
              className={clsx(
                'text-xs font-bold px-2 py-0.5 rounded-full mt-1 border shadow-xs',
                value >= 80 ? 'bg-teal-50 text-teal-700 border-teal-200' :
                value >= 60 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                'bg-red-50 text-red-600 border-red-200'
              )}
            >
              Grade {letterGrade}
            </span>
          )}
        </div>
      </div>
      <div className="flex flex-col items-center text-center">
        {qualifier && (
          <span
            className={clsx(
              'text-[11px] font-semibold px-2 py-0.5 rounded-md mb-0.5',
              value >= 80 ? 'bg-teal-50 text-teal-700' :
              value >= 60 ? 'bg-amber-50 text-amber-700' :
              'bg-red-50 text-red-600'
            )}
          >
            {qualifier}
          </span>
        )}
        {label && <p className="text-xs text-slate-400 font-medium">{label}</p>}
      </div>
    </div>
  );
};

export default ScoreGauge;
