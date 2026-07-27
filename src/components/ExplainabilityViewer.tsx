import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import type { ExplainabilityResult, ExplainabilitySignal } from '../types';

interface ExplainabilityViewerProps {
  explainability?: ExplainabilityResult;
}

const ExplainabilityViewer: React.FC<ExplainabilityViewerProps> = ({
  explainability,
}) => {
  const [activeSignal, setActiveSignal] =
    useState<ExplainabilitySignal | null>(null);

  if (!explainability) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
        <div className="flex items-center gap-2 text-slate-600">
          <Info size={16} />
          <p className="text-sm">
            Explainability data is not available for this report.
          </p>
        </div>
      </div>
    );
  }

  const signals = explainability.signals || [];

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Composite novelty score
            </p>

            <div className="mt-1 flex items-end gap-2">
              <span className="text-3xl font-bold text-navy-900">
                {explainability.composite_novelty_score.toFixed(1)}
              </span>

              <span className="pb-1 text-sm text-slate-500">/ 100</span>
            </div>
          </div>

          <div className="text-right">
            <span className="inline-flex rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
              {explainability.novelty_band}
            </span>

            <p className="mt-2 text-xs text-slate-500">
              Model: {explainability.explainer_mode}
            </p>
          </div>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-slate-700">
          {explainability.overall_summary}
        </p>
      </div>

      <div className="space-y-3">
        {signals.map((signal) => {
          const isOpen = activeSignal?.signal_key === signal.signal_key;
          const contributionWidth = Math.min(
            Math.max(signal.percentage_of_max, 0),
            100,
          );

          return (
            <div
              key={signal.signal_key}
              className="overflow-hidden rounded-xl border border-slate-200 bg-white"
            >
              <button
                type="button"
                onClick={() => setActiveSignal(isOpen ? null : signal)}
                className="w-full p-4 text-left transition hover:bg-slate-50"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-navy-900">
                        {signal.signal_name}
                      </h3>

                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        Weight {(signal.weight * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-teal-500"
                        style={{ width: `${contributionWidth}%` }}
                      />
                    </div>

                    <div className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-slate-500">
                      <span>
                        Raw value: {signal.raw_value.toFixed(4)}
                      </span>

                      <span>
                        Contribution:{' '}
                        {signal.weighted_contribution.toFixed(2)} /{' '}
                        {signal.max_possible_contribution.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  <div className="pt-1 text-slate-400">
                    {isOpen ? (
                      <ChevronUp size={18} />
                    ) : (
                      <ChevronDown size={18} />
                    )}
                  </div>
                </div>
              </button>

              {isOpen && (
                <div className="border-t border-slate-100 bg-slate-50 px-4 py-4">
                  <p className="text-sm leading-relaxed text-slate-700">
                    {signal.explanation}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ExplainabilityViewer;