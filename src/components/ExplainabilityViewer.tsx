import React, { useState } from 'react';
import clsx from 'clsx';
import { Info } from 'lucide-react';
import type { ExplainabilityAnnotation } from '../types';

interface ExplainabilityViewerProps {
  annotations: ExplainabilityAnnotation[];
}

const getHighlightStyle = (weight: number): React.CSSProperties => {
  const abs = Math.abs(weight);
  const opacity = Math.min(0.15 + abs * 0.5, 0.65);
  if (weight > 0.2) return { backgroundColor: `rgba(30, 127, 114, ${opacity})`, borderRadius: 3 };
  if (weight < -0.2) return { backgroundColor: `rgba(239, 68, 68, ${opacity})`, borderRadius: 3 };
  return {};
};

const getWeightLabel = (weight: number): { label: string; color: string } => {
  if (weight > 0.7) return { label: 'Strong Positive', color: 'text-teal-700' };
  if (weight > 0.2) return { label: 'Positive', color: 'text-teal-600' };
  if (weight < -0.5) return { label: 'Strong Negative', color: 'text-red-700' };
  if (weight < -0.2) return { label: 'Negative', color: 'text-red-600' };
  return { label: 'Neutral', color: 'text-slate-500' };
};

const ExplainabilityViewer: React.FC<ExplainabilityViewerProps> = ({ annotations }) => {
  const [activeAnnotation, setActiveAnnotation] = useState<ExplainabilityAnnotation | null>(null);

  if (annotations.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500">
        No evidence annotations have been generated for this report yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center gap-6 text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(30, 127, 114, 0.4)' }} />
          Positive impact
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.4)' }} />
          Negative impact
        </div>
        <div className="flex items-center gap-1.5">
          <Info size={13} />
          Hover for details
        </div>
      </div>

      {/* Document */}
      <div className="bg-white rounded-xl border border-slate-100 p-6 leading-relaxed text-slate-700 text-sm space-y-2">
        {annotations.map((annotation, i) => (
          <span
            key={i}
            style={getHighlightStyle(annotation.weight)}
            className="px-0.5 cursor-pointer relative group"
            onClick={() => setActiveAnnotation(activeAnnotation?.sentence === annotation.sentence ? null : annotation)}
          >
            {annotation.sentence}{' '}
          </span>
        ))}
      </div>

      {/* Detail panel */}
      {activeAnnotation && (
        <div className="bg-navy-900 text-white rounded-xl p-5 space-y-3 animate-fade-in">
          <div className="flex items-start justify-between gap-4">
            <p className="text-sm font-medium text-white/90 italic">"{activeAnnotation.sentence}"</p>
            <span className={clsx(
              'text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0',
              activeAnnotation.weight > 0 ? 'bg-teal-500/20 text-teal-300' : 'bg-red-500/20 text-red-300'
            )}>
              {getWeightLabel(activeAnnotation.weight).label}
            </span>
          </div>
          <p className="text-sm text-white/70">{activeAnnotation.reason}</p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/50">Impact weight:</span>
            <div className="flex-1 bg-white/10 rounded-full h-2">
              <div
                className={clsx('h-2 rounded-full', activeAnnotation.weight > 0 ? 'bg-teal-400' : 'bg-red-400')}
                style={{ width: `${Math.abs(activeAnnotation.weight) * 100}%` }}
              />
            </div>
            <span className="text-xs text-white/50">{(activeAnnotation.weight * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExplainabilityViewer;
