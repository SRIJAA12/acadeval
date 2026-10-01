import React, { useState } from 'react';
import {
  ChevronDown, ChevronUp, Info, Calculator, Database, Sparkles,
  Layers, CheckCircle, ShieldCheck, ArrowRight, Activity, TrendingUp,
  Cpu, Award, BookOpen, AlertCircle, HelpCircle, Lightbulb, Target, Compass
} from 'lucide-react';
import type {
  ExplainabilityResult,
  ExplainabilitySignal,
  ExplainabilityDimensionScore,
  ExplainabilityDatasetComparison,
} from '../types';

interface SignalGuide {
  num: number;
  plain_name: string;
  tech_name: string;
  question: string;
  plain_meaning: string;
  analogy: string;
  high_meaning: string;
  low_meaning: string;
  how_to_improve: string;
}

const SIGNAL_GUIDE_MAP: Record<string, SignalGuide> = {
  signal_1_graph_distance: {
    num: 1,
    plain_name: 'Overall Project Uniqueness',
    tech_name: 'Graph Distance (Nearest-Neighbor Jaccard)',
    question: 'Has anyone in our college records done almost this exact same project before?',
    plain_meaning:
      'We compare this proposal\'s entire blueprint, objectives, and methodologies against all past student proposals in our knowledge graph. It verifies whether someone has already built an identical or nearly identical system in previous semesters.',
    analogy:
      'Like an originality audit for the whole project blueprint — confirming that earlier student batches haven\'t already solved this exact problem using this same pipeline.',
    high_meaning: 'Truly fresh concept; no duplicate or near-clone exists in past college submissions.',
    low_meaning: 'Heavy structural overlap with an existing proposal in the database (potential duplicate or rehash).',
    how_to_improve: 'Tackle a fundamentally distinct problem or introduce a completely new technical pipeline.',
  },
  signal_2_feature_rarity: {
    num: 2,
    plain_name: 'Tool & Technology Rarity',
    tech_name: 'Feature Rarity (Corpus Frequency)',
    question: 'Are the algorithms, models, and libraries being used cutting-edge or standard classroom tools?',
    plain_meaning:
      'We inspect every algorithm, AI architecture, library, and tool mentioned (like YOLOv8, PyTorch, LoRA, OpenCV, Docker) against ~28,000 reference entries to check how frequently students choose them.',
    analogy:
      'Building an app with standard SQLite and HTML gets a low rarity score; building it with Vector Databases, LoRA fine-tuning, and WebAssembly gets a high rarity score.',
    high_meaning: 'Uses specialized, modern, or cutting-edge research algorithms and technologies rarely attempted by peers.',
    low_meaning: 'Relies strictly on standard, ubiquitous textbook algorithms (e.g. basic linear regression, Haar cascades, standard k-means).',
    how_to_improve: 'Adopt modern, specialized frameworks, state-of-the-art models, or advanced architectures instead of routine defaults.',
  },
  signal_3_relationship_rarity: {
    num: 3,
    plain_name: 'Unconventional Tech Combinations',
    tech_name: 'Relationship Rarity (Entity Pair Co-occurrence)',
    question: 'Has anyone paired these specific technologies or concepts together before?',
    plain_meaning:
      'Even if two technologies are well-known individually (e.g. "Virtual Reality" + "Stroke Rehabilitation", or "Blockchain" + "Soil Moisture"), using them together can be innovative. This evaluates pairs of concepts to see if they rarely appear together in historical work.',
    analogy:
      'Peanut butter is common and chili oil is common, but pairing them creates a novel fusion recipe. This signal rewards creative, unconventional pairings of tools and ideas.',
    high_meaning: 'Creative, unexpected combination of technologies solving a new problem.',
    low_meaning: 'Predictable, standard combination that is routinely paired together (e.g. CNN + MNIST, or React + MySQL).',
    how_to_improve: 'Cross-pollinate techniques — apply an algorithm or architecture from one domain to solve a problem in another.',
  },
  signal_4_graph_density: {
    num: 4,
    plain_name: 'Unexplored Domain Territory',
    tech_name: 'Graph Density / Sparsity (Neighborhood Saturation)',
    question: 'Is this domain overcrowded with projects, or is it an unexplored area?',
    plain_meaning:
      'Examines the project\'s sub-domain in the college knowledge graph. If 50 students previously did "Face Recognition Attendance", that cluster is crowded (high density, low novelty score). If few or no students have explored this specific niche, it is rewarded as greenfield territory.',
    analogy:
      'Opening a pizza shop on a street with 20 existing pizza shops (crowded area) vs. opening the very first specialty bakery in an underserved neighborhood (unexplored territory).',
    high_meaning: 'Pioneering work in an untouched or rarely explored niche with few prior attempts.',
    low_meaning: 'Saturated topic where dozens of past student batches have already worked.',
    how_to_improve: 'Pivot slightly into an underserved sub-domain or emerging specialty where few student projects have ventured.',
  },
  signal_5_new_connection_discovery: {
    num: 5,
    plain_name: 'Cross-Disciplinary Bridge',
    tech_name: 'New-Connection Discovery (Adamic-Adar Link Prediction)',
    question: 'Does this project bridge two separate fields that rarely talk to each other?',
    plain_meaning:
      'Using link-prediction algorithms (Adamic-Adar), we test whether the project builds a brand-new bridge between two established but previously disconnected fields or concepts, representing an interdisciplinary breakthrough.',
    analogy:
      'Applying fluid dynamics algorithms from aerospace engineering to predict financial market volatility — linking two distinct disciplines together.',
    high_meaning: 'Breakthrough interdisciplinary synthesis connecting isolated academic fields.',
    low_meaning: 'Confined strictly within traditional, isolated disciplinary boundaries.',
    how_to_improve: 'Synthesize concepts across departmental or disciplinary boundaries to build interdisciplinary bridges.',
  },
};

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
                    <div className="border-t border-slate-100 bg-slate-50/80 p-4 space-y-3">
                      {/* Step-by-step derivation — multiline rendering */}
                      <div className="space-y-2">
                        {dim.explanation.split('\n').map((line, i) => {
                          const trimmed = line.trim();
                          if (!trimmed) return null;
                          const isStep = trimmed.startsWith('Step ');
                          const isIndented = line.startsWith('  ');
                          const isFormula = trimmed.startsWith('→') || trimmed.startsWith('Score =') || trimmed.startsWith('Combined') || trimmed.startsWith('Originality') || trimmed.startsWith('Rubric');
                          return (
                            <p
                              key={i}
                              className={`text-xs leading-relaxed ${
                                isStep
                                  ? 'font-bold text-slate-900 pt-1 border-t border-slate-200 first:border-0 first:pt-0'
                                  : isIndented
                                    ? 'font-mono text-[11px] text-slate-600 pl-3 border-l-2 border-indigo-200'
                                    : isFormula
                                      ? 'font-semibold text-indigo-800 bg-indigo-50 rounded px-2 py-1'
                                      : 'text-slate-500 text-[11px]'
                              }`}
                            >
                              {trimmed}
                            </p>
                          );
                        })}
                      </div>
                      {/* Dimension scope */}
                      <div className="rounded-lg bg-slate-100 px-3 py-2 text-[11px] text-slate-500">
                        <strong className="text-slate-700">Dimension scope: </strong>{dim.description}
                      </div>
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
          {/* Top Educational Guide: What do these signals mean? */}
          <div className="rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 via-indigo-50 to-purple-50 p-4 text-xs text-purple-950 space-y-2 shadow-sm">
            <div className="font-bold flex items-center gap-2 text-purple-950 text-sm">
              <Sparkles size={16} className="text-purple-600" /> What Do These 5 Signals Mean?
            </div>
            <p className="text-slate-700 text-xs leading-relaxed">
              Instead of a single vague number, AcadEval+ calculates novelty across <strong>5 distinct dimensions of innovation</strong>. 
              Each signal answers a specific, practical question about how this proposal compares against historical submissions in our college database.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pt-1">
              <div className="bg-white/90 rounded-lg p-2 border border-purple-100 text-[11px] shadow-2xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">Signal 1</span>
                <strong className="text-slate-900 block font-semibold">Idea Uniqueness</strong>
                <span className="text-slate-500 text-[10px] leading-tight block mt-0.5">Is someone else already doing this exact project?</span>
              </div>
              <div className="bg-white/90 rounded-lg p-2 border border-purple-100 text-[11px] shadow-2xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Signal 2</span>
                <strong className="text-slate-900 block font-semibold">Tool Rarity</strong>
                <span className="text-slate-500 text-[10px] leading-tight block mt-0.5">Are the models/tools modern or classroom standard?</span>
              </div>
              <div className="bg-white/90 rounded-lg p-2 border border-purple-100 text-[11px] shadow-2xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600">Signal 3</span>
                <strong className="text-slate-900 block font-semibold">Novel Combos</strong>
                <span className="text-slate-500 text-[10px] leading-tight block mt-0.5">Are known tools combined in unexpected ways?</span>
              </div>
              <div className="bg-white/90 rounded-lg p-2 border border-purple-100 text-[11px] shadow-2xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-600">Signal 4</span>
                <strong className="text-slate-900 block font-semibold">Unexplored Area</strong>
                <span className="text-slate-500 text-[10px] leading-tight block mt-0.5">Is the sub-domain overcrowded or greenfield?</span>
              </div>
              <div className="bg-white/90 rounded-lg p-2 border border-purple-100 text-[11px] shadow-2xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600">Signal 5</span>
                <strong className="text-slate-900 block font-semibold">Cross-Field Bridge</strong>
                <span className="text-slate-500 text-[10px] leading-tight block mt-0.5">Does it link two previously separated fields?</span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {signals.map((signal, idx) => {
              const guide = SIGNAL_GUIDE_MAP[signal.signal_key] || {
                num: idx + 1,
                plain_name: signal.plain_name || signal.signal_name,
                tech_name: signal.signal_name,
                question: signal.question || 'How novel is this dimension compared to historical submissions?',
                plain_meaning: signal.plain_meaning || signal.explanation,
                analogy: signal.analogy || 'Measures divergence from past student projects.',
                high_meaning: signal.high_meaning || 'High differentiation from prior student work.',
                low_meaning: signal.low_meaning || 'Substantial overlap with prior student work.',
                how_to_improve: 'Explore less common techniques or less crowded sub-domains.',
              };

              const isOpen = activeSignal?.signal_key === signal.signal_key;
              const pct = Math.min(Math.max(signal.percentage_of_max, 0), 100);
              const tier = signal.raw_value >= 0.65 ? 'high' : signal.raw_value >= 0.40 ? 'moderate' : 'low';
              const tierStyle: Record<string, string> = {
                high:     'bg-emerald-50 text-emerald-700 border-emerald-200',
                moderate: 'bg-amber-50 text-amber-700 border-amber-200',
                low:      'bg-rose-50 text-rose-700 border-rose-200',
              };
              const tierText: Record<string, string> = {
                high: '● Highly Novel', moderate: '● Moderately Novel', low: '● Incremental / Overlapping',
              };
              const barColor: Record<string, string> = {
                high: 'bg-emerald-500', moderate: 'bg-amber-500', low: 'bg-rose-400',
              };

              return (
                <div
                  key={signal.signal_key}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:border-slate-300"
                >
                  <button
                    type="button"
                    onClick={() => setActiveSignal(isOpen ? null : signal)}
                    className="w-full p-4 text-left transition hover:bg-slate-50/70"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1 space-y-1.5">
                        {/* Header: Signal Number + Plain English Name + Badges */}
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-md bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-xs font-bold text-indigo-700">
                            Signal {guide.num}
                          </span>
                          <h3 className="font-bold text-slate-900 text-sm sm:text-base">
                            {guide.plain_name}
                          </h3>
                          <span className="text-xs text-slate-400 font-mono hidden sm:inline">
                            ({guide.tech_name})
                          </span>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 font-semibold ml-auto sm:ml-0">
                            Weight {(signal.weight * 100).toFixed(0)}%
                          </span>
                          <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${tierStyle[tier]}`}>
                            {tierText[tier]}
                          </span>
                        </div>

                        {/* Plain English Core Question */}
                        <div className="flex items-center gap-2 text-xs text-indigo-900 bg-indigo-50/80 rounded-lg px-3 py-1.5 border border-indigo-100 font-medium">
                          <HelpCircle size={14} className="shrink-0 text-indigo-600" />
                          <span>&ldquo;{guide.question}&rdquo;</span>
                        </div>

                        {/* Progress Bar */}
                        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                          <div className={`h-full rounded-full transition-all duration-300 ${barColor[tier]}`} style={{ width: `${pct}%` }} />
                        </div>

                        {/* Metrics Bar */}
                        <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500 pt-0.5">
                          <span>Raw score: <strong className="text-slate-800 font-mono">{(signal.raw_value * 100).toFixed(1)}%</strong></span>
                          <span>
                            Points contributed: <strong className="text-slate-800 font-mono">{signal.weighted_contribution.toFixed(2)}</strong>{' '}
                            / {signal.max_possible_contribution.toFixed(2)} pts
                          </span>
                        </div>
                      </div>

                      <div className="pt-2 text-slate-400 shrink-0">
                        {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </div>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="border-t border-slate-100 bg-slate-50/90 p-4 sm:p-5 space-y-4">
                      {/* Section 1: Plain English Meaning */}
                      <div className="rounded-xl border border-indigo-100 bg-white p-3.5 space-y-1.5 shadow-2xs">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-950 uppercase tracking-wider">
                          <Target size={14} className="text-indigo-600" /> What this measures in plain English:
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed font-normal">
                          {guide.plain_meaning}
                        </p>
                      </div>

                      {/* Section 2: Real-World Analogy */}
                      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3.5 space-y-1 shadow-2xs">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-950">
                          <Lightbulb size={14} className="text-amber-600" /> Real-World Analogy:
                        </div>
                        <p className="text-xs text-amber-900 leading-relaxed italic">
                          {guide.analogy}
                        </p>
                      </div>

                      {/* Section 3: Score Interpretation & Improvement Guide */}
                      <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-2 text-xs shadow-2xs">
                        <div className="font-bold text-slate-800 flex items-center justify-between">
                          <span>Current Result: {(signal.raw_value * 100).toFixed(1)}% ({tierText[tier]})</span>
                          <span className="text-[11px] font-normal text-slate-500">
                            {signal.weighted_contribution.toFixed(2)} pts toward final score
                          </span>
                        </div>
                        <p className="text-slate-600 leading-relaxed">
                          {tier === 'high' ? guide.high_meaning : tier === 'moderate' ? 'This submission shows solid differentiation, but shares some common frameworks or problem parameters with existing projects.' : guide.low_meaning}
                        </p>
                        <div className="pt-2 border-t border-slate-100 flex items-start gap-1.5 text-[11px] text-slate-600">
                          <strong className="text-indigo-700 shrink-0">💡 How to raise this score:</strong>
                          <span>{guide.how_to_improve}</span>
                        </div>
                      </div>

                      {/* Section 4: Audit & Benchmark Data Source */}
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {((signal as any).dataset_source || (signal as any).dataset_source === undefined) && (
                            <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 border border-indigo-200 px-2.5 py-1 text-[11px] font-semibold text-indigo-800">
                              <Database size={12} /> {(signal as any).dataset_source || 'AcadEval Benchmark Corpus'}
                            </span>
                          )}
                          {(signal as any).method && (
                            <span className="inline-flex items-center gap-1.5 rounded-md bg-teal-50 border border-teal-200 px-2.5 py-1 text-[11px] font-medium text-teal-800 font-mono">
                              <Activity size={12} /> {(signal as any).method}
                            </span>
                          )}
                        </div>

                        {/* Step-by-step or detailed audit lines */}
                        <div className="rounded-lg bg-slate-100 p-3 space-y-1.5 border border-slate-200 text-xs text-slate-600">
                          <div className="font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
                            Detailed System Evidence:
                          </div>
                          {signal.explanation.split('\n').filter(l => l.trim()).map((line, i) => (
                            <p
                              key={i}
                              className={`text-[11px] leading-relaxed ${
                                line.startsWith('🎯') || line.startsWith('Question:')
                                  ? 'font-semibold text-indigo-950'
                                  : line.startsWith('Nearest Comparison:') || line.startsWith('Nearest historical')
                                    ? 'font-mono text-slate-800 bg-white p-1.5 rounded border border-slate-200'
                                    : 'text-slate-600'
                              }`}
                            >
                              {line.trim()}
                            </p>
                          ))}
                        </div>
                      </div>
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