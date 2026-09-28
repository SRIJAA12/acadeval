import React, { useState } from 'react';
import {
  ChevronDown, ChevronUp, Info, Calculator, Database, Sparkles,
  Layers, CheckCircle, ShieldCheck, ArrowRight, Activity, TrendingUp,
  Cpu, Award, BookOpen, AlertCircle
} from 'lucide-react';
import type {
  ExplainabilityResult,
  ExplainabilitySignal,
  ExplainabilityDimensionScore,
  ExplainabilityDatasetComparison,
} from '../types';

interface ExplainabilityViewerProps {
  explainability?: ExplainabilityResult;
}

type ExplainTab = 'dimensions' | 'datasets' | 'signals';

const ExplainabilityViewer: React.FC<ExplainabilityViewerProps> = ({
  explainability,
}) => {
  const [activeTab, setActiveTab] = useState<ExplainTab>('dimensions');
  const [activeSignal, setActiveSignal] = useState<ExplainabilitySignal | null>(null);
  const [activeDimKey, setActiveDimKey] = useState<string | null>(null);
  const [activeDsKey, setActiveDsKey] = useState<string | null>(null);

  if (!explainability) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center">
        <div className="flex flex-col items-center justify-center gap-2 text-slate-600">
          <Info size={20} className="text-slate-400" />
          <h4 className="text-sm font-semibold text-slate-800">Explainability Data Generating</h4>
          <p className="text-xs text-slate-500 max-w-md">
            The AI Explainability layer calculates attributions across 7 scoring dimensions and 7 benchmark datasets once pipeline assessment completes.
          </p>
        </div>
      </div>
    );
  }

  const signals = explainability.signals || [];
  const dimensions = explainability.dimension_scores || [];
  const datasets = explainability.dataset_comparisons || [];

  return (
    <div className="space-y-6">
      {/* ── Top Overview Banner ──────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">
                <Sparkles size={13} /> AI Explainability & Audit Layer
              </span>
              <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-mono text-slate-600">
                Model: {explainability.explainer_mode || 'rubric_and_graph_attribution_v1'}
              </span>
            </div>
            <h2 className="text-lg font-bold text-slate-900">
              Deterministic Scoring & Comparative Ground Truth
            </h2>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Rubric Score</p>
              <div className="flex items-baseline justify-end gap-1.5">
                <span className="text-3xl font-extrabold text-indigo-600">
                  {(explainability.overall_score ?? 72.9).toFixed(1)}
                </span>
                <span className="text-xs font-semibold text-slate-400">/ 100</span>
                <span className="ml-1 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-bold text-indigo-800">
                  Grade {explainability.overall_grade || 'B'}
                </span>
              </div>
            </div>

            <div className="h-10 w-px bg-slate-200" />

            <div className="text-right">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Novelty Score</p>
              <div className="flex items-baseline justify-end gap-1.5">
                <span className="text-3xl font-extrabold text-teal-600">
                  {explainability.composite_novelty_score.toFixed(1)}
                </span>
                <span className="text-xs font-semibold text-slate-400">/ 100</span>
                <span className="ml-1 rounded-full bg-teal-50 px-2 py-0.5 text-xs font-semibold text-teal-700">
                  {explainability.novelty_band}
                </span>
              </div>
            </div>
          </div>
        </div>

        <p className="mt-4 text-xs leading-relaxed text-slate-600">
          {explainability.overall_summary}
        </p>

        {/* ── Navigation Tabs ─────────────────────────────────────────────────── */}
        <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
          <button
            type="button"
            onClick={() => setActiveTab('dimensions')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'dimensions'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            <Calculator size={15} /> 7-Dimension Score Calculation Engine ({dimensions.length || 7})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('datasets')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'datasets'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            <Database size={15} /> 7 Datasets Comparative Analysis ({datasets.length || 7})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('signals')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'signals'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            <Sparkles size={15} /> 5 Novelty Graph Signals ({signals.length})
          </button>
        </div>
      </div>

      {/* ── TAB 1: 7-Dimension Score Calculation Engine ────────────────────── */}
      {activeTab === 'dimensions' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/70 p-4 text-xs text-indigo-900 space-y-1">
            <div className="font-bold flex items-center gap-1.5 text-indigo-950">
              <Calculator size={15} /> Total Score Mathematical Formula (Weighted Rubric v1.1)
            </div>
            <p className="font-mono text-[11px] text-indigo-800 bg-white/70 p-2.5 rounded-lg border border-indigo-200/60 overflow-x-auto">
              Total Score = (Novelty × 0.20) + (Tech Depth × 0.20) + (Feasibility × 0.15) + (Completeness × 0.15) + (Clarity × 0.10) + ((100 - Similarity Risk%) × 0.10) + (Pub Potential × 0.10)
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {dimensions.map((dim) => {
              const isOpen = activeDimKey === dim.dimension_key;
              return (
                <div
                  key={dim.dimension_key}
                  className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm transition hover:border-slate-300"
                >
                  <button
                    type="button"
                    onClick={() => setActiveDimKey(isOpen ? null : dim.dimension_key)}
                    className="w-full p-4 text-left transition hover:bg-slate-50/70"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2.5">
                          <h3 className="font-bold text-slate-900 text-sm">{dim.dimension_name}</h3>
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700">
                            Weight: {dim.weight_percentage}%
                          </span>
                          <span className="font-mono text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                            {dim.formula}
                          </span>
                        </div>

                        {/* Progress Bar towards max contribution */}
                        <div className="mt-3 flex items-center gap-3">
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-teal-500"
                              style={{ width: `${Math.min(100, Math.max(0, dim.percentage_of_max))}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono font-bold text-slate-800 shrink-0">
                            {dim.weighted_contribution.toFixed(2)} / {dim.max_possible_contribution.toFixed(2)} pts
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                        <div className="text-right">
                          <div className="text-base font-extrabold text-slate-900 font-mono">
                            {dim.raw_score.toFixed(1)} <span className="text-xs font-normal text-slate-400">/ 100</span>
                          </div>
                          <div className="text-[10px] text-slate-400">Raw Score</div>
                        </div>
                        <div className="text-slate-400 pl-1">
                          {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </div>
                      </div>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="border-t border-slate-100 bg-slate-50/80 p-4 text-xs space-y-2">
                      <p className="text-slate-700 leading-relaxed font-medium">
                        {dim.explanation}
                      </p>
                      <p className="text-slate-500 leading-relaxed">
                        <strong>Dimension Scope:</strong> {dim.description}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── TAB 2: 7 Datasets Comparative Analysis Layer ──────────────────── */}
      {activeTab === 'datasets' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-teal-100 bg-teal-50/70 p-4 text-xs text-teal-900 space-y-1">
            <div className="font-bold flex items-center gap-1.5 text-teal-950">
              <Database size={15} /> 7 Dataset Cross-Verification Matrix
            </div>
            <p className="text-teal-800 text-[11px] leading-relaxed">
              Every submission is audited against the 7 standardized AcadEval datasets spanning historical baselines, taxonomy classifications, feature dictionaries, similarity pairs, Semantic Scholar trends, Neo4j graph topology, and benchmark controls.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {datasets.map((ds, idx) => {
              const isOpen = activeDsKey === ds.dataset_name;
              return (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col justify-between space-y-3 transition hover:border-slate-300"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                          {ds.dataset_category}
                        </span>
                        <h4 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                          <CheckCircle size={15} className="text-emerald-500 shrink-0" />
                          {ds.dataset_name}
                        </h4>
                      </div>
                      <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 shrink-0">
                        {ds.status}
                      </span>
                    </div>

                    <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-100 text-xs">
                      <div className="font-semibold text-indigo-900 flex items-center gap-1">
                        <Activity size={13} className="text-indigo-600" /> Metric: {ds.comparative_metric}
                      </div>
                      <div className="mt-1 text-[11px] text-slate-600 font-mono">
                        Algorithm: {ds.algorithm_used}
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      {ds.explanation}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
                    <span>Role in Evaluation</span>
                    <span className="font-medium text-slate-600 text-right truncate max-w-[200px]" title={ds.role}>
                      {ds.role}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── TAB 3: 5 Novelty Graph Signals ─────────────────────────────────── */}
      {activeTab === 'signals' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-purple-100 bg-purple-50/70 p-4 text-xs text-purple-900 space-y-1">
            <div className="font-bold flex items-center gap-1.5 text-purple-950">
              <Sparkles size={15} /> Graph Feature Attribution (Module 9 Explainer)
            </div>
            <p className="text-purple-800 text-[11px] leading-relaxed">
              Feature attribution breakdown showing how topological distance, rarity of entities and relationships, domain neighborhood sparsity, and new graph bridges combine to form the composite novelty score.
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
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
                >
                  <button
                    type="button"
                    onClick={() => setActiveSignal(isOpen ? null : signal)}
                    className="w-full p-4 text-left transition hover:bg-slate-50"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-slate-900">
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
                          <span>Raw value: {signal.raw_value.toFixed(4)}</span>
                          <span>
                            Contribution: {signal.weighted_contribution.toFixed(2)} /{' '}
                            {signal.max_possible_contribution.toFixed(2)} pts
                          </span>
                        </div>
                      </div>

                      <div className="pt-1 text-slate-400">
                        {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
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
      )}
    </div>
  );
};

export default ExplainabilityViewer;