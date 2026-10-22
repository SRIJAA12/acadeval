import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getQualitySummary, getQualityAblation, getQualityRuns, getRecentTelemetry,
  getFacultyAgreementLatest, triggerBenchmarkRun,
} from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import {
  Activity, AlertTriangle, CheckCircle2, XCircle, PlayCircle, Network,
  Gauge, Users, Beaker, HelpCircle,
} from 'lucide-react';
import type { QualityMetricPoint } from '../../types';

// Every metric is shown on its own, with n and a confidence interval where
// available. This dashboard never computes or displays a single combined
// "accuracy %" — see the project's quality-architecture notes for why.

const fmtPct = (v: number | null) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}%`);
const fmtNum = (v: number | null, digits = 3) => (v === null || v === undefined ? '—' : v.toFixed(digits));
const fmtMs = (v: number | null) => (v === null || v === undefined ? '—' : `${v.toFixed(0)} ms`);

const MetricCard: React.FC<{ m: QualityMetricPoint; format?: 'pct' | 'num' | 'ms' }> = ({ m, format = 'num' }) => {
  const formatted = format === 'pct' ? fmtPct(m.value) : format === 'ms' ? fmtMs(m.value) : fmtNum(m.value);
  const statusColor = m.passed === true ? 'text-emerald-600' : m.passed === false ? 'text-red-600' : 'text-slate-600';
  const belowMinN = Boolean(m.details?.below_min_n);
  return (
    <div className={`p-4 rounded-xl border bg-white ${belowMinN ? 'opacity-50' : ''}`} title={belowMinN ? 'Below minimum sample size — shown for transparency, not yet reliable' : undefined}>
      <div className="text-xs text-slate-500 font-medium truncate" title={m.metric}>{m.metric}</div>
      <div className={`text-2xl font-bold mt-1 ${statusColor}`}>{formatted}</div>
      <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
        <span>n={m.n ?? '—'}</span>
        {m.ci_low !== null && m.ci_high !== null && (
          <span>CI [{fmtNum(m.ci_low, 2)}, {fmtNum(m.ci_high, 2)}]</span>
        )}
        {m.target !== null && (
          <span className="ml-auto flex items-center gap-1">
            {m.passed ? <CheckCircle2 size={12} className="text-emerald-500" /> : <XCircle size={12} className="text-red-400" />}
            target {m.target_op ?? '>='} {fmtNum(m.target, 2)}
          </span>
        )}
      </div>
    </div>
  );
};

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; subtitle?: string }> = ({ icon, title, subtitle }) => (
  <div className="flex items-center gap-3 mb-3">
    <div className="w-9 h-9 rounded-lg bg-[#1B2A4A] text-white flex items-center justify-center flex-shrink-0">{icon}</div>
    <div>
      <h2 className="font-semibold text-slate-800">{title}</h2>
      {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
    </div>
  </div>
);

const QualityDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [triggering, setTriggering] = useState(false);

  const summaryQ = useQuery({ queryKey: ['quality', 'summary'], queryFn: getQualitySummary, refetchInterval: 15_000 });
  const ablationQ = useQuery({ queryKey: ['quality', 'ablation'], queryFn: getQualityAblation, refetchInterval: 30_000 });
  const runsQ = useQuery({ queryKey: ['quality', 'runs'], queryFn: () => getQualityRuns(undefined, 20), refetchInterval: 15_000 });
  const telemetryQ = useQuery({ queryKey: ['quality', 'telemetry'], queryFn: () => getRecentTelemetry(25), refetchInterval: 10_000 });
  const facultyQ = useQuery({ queryKey: ['quality', 'faculty'], queryFn: getFacultyAgreementLatest, refetchInterval: 30_000 });

  const runBenchmark = useMutation({
    mutationFn: () => triggerBenchmarkRun('manual'),
    onMutate: () => setTriggering(true),
    onSettled: () => {
      setTriggering(false);
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['quality'] }), 3000);
    },
  });

  if (summaryQ.isLoading) return <LoadingState message="Loading quality dashboard..." />;
  if (summaryQ.isError || !summaryQ.data) return <ErrorState retry={() => summaryQ.refetch()} />;

  const { runs, current_method_fingerprint } = summaryQ.data;

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Evaluation &amp; Quality</h1>
          <p className="text-sm text-slate-500 mt-1">
            Every number below is measured independently — none of this is combined into a single "accuracy" score.
          </p>
        </div>
        <button
          onClick={() => runBenchmark.mutate()}
          disabled={triggering}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1B2A4A] text-white text-sm font-medium hover:bg-[#243867] disabled:opacity-50"
        >
          <PlayCircle size={16} /> {triggering ? 'Queuing…' : 'Run benchmark now'}
        </button>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
        <HelpCircle size={14} />
        Current scoring method fingerprint: <code className="font-mono">{current_method_fingerprint}</code>
        — a benchmark run is triggered automatically whenever this changes.
      </div>

      {/* Faculty agreement banner — the one metric touching real ground truth */}
      <div className="p-4 rounded-xl border border-amber-200 bg-amber-50 flex items-start gap-3">
        <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-amber-900">
          <strong>Agreement with real faculty judgement is not yet established.</strong>{' '}
          {facultyQ.data && facultyQ.data.metrics.length > 0 ? (
            <>See the Faculty Agreement section below — all values are shown for transparency even where n is small.</>
          ) : (
            <>No faculty evaluations have been recorded yet. Benchmark and graph-integrity metrics below measure the system
            against itself (formula correctness, synthetic duplicate detection, structural integrity) — they do not prove
            the scores match real academic judgement.</>
          )}
        </div>
      </div>

      {/* Benchmark */}
      <section>
        <SectionHeader icon={<Beaker size={18} />} title="Benchmark"
          subtitle={runs.benchmark ? `${runs.benchmark.n_cases ?? 0} cases · ${new Date(runs.benchmark.started_at).toLocaleString()} · ${runs.benchmark.trigger}` : 'No run yet'} />
        {runs.benchmark ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {runs.benchmark.metrics.map((m) => (
              <MetricCard key={`${m.metric}:${m.slice}`} m={m} format={m.metric.includes('rate') || m.metric.includes('precision') || m.metric.includes('recall') || m.metric.includes('coverage') ? 'pct' : 'num'} />
            ))}
          </div>
        ) : (
          <EmptyState icon={<Beaker size={28} />} title="No benchmark run yet" description='Click "Run benchmark now" above, or wait for the next scheduled run.' />
        )}
      </section>

      {/* Graph integrity */}
      <section>
        <SectionHeader icon={<Network size={18} />} title="Graph Integrity"
          subtitle={runs.graph_integrity ? new Date(runs.graph_integrity.started_at).toLocaleString() : 'No run yet'} />
        {runs.graph_integrity ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {runs.graph_integrity.metrics.map((m) => (
              <MetricCard key={m.metric} m={m} format={m.metric.includes('rate') ? 'pct' : 'num'} />
            ))}
          </div>
        ) : (
          <EmptyState icon={<Network size={28} />} title="No graph-integrity run yet" />
        )}
      </section>

      {/* Online telemetry (live) */}
      <section>
        <SectionHeader icon={<Gauge size={18} />} title="Live Scoring Telemetry"
          subtitle="Rolled up hourly from every real submission's run" />
        {runs.online_rollup ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {runs.online_rollup.metrics.map((m) => (
              <MetricCard key={m.metric} m={m} format={m.metric.startsWith('latency_ms') ? 'ms' : m.metric.includes('rate') || m.metric.includes('coverage') ? 'pct' : 'num'} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 mb-4">No rollup yet — runs hourly.</p>
        )}

        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="text-left px-3 py-2">Project</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2">Total</th>
                <th className="text-left px-3 py-2">Novelty</th>
                <th className="text-left px-3 py-2">Overall</th>
                <th className="text-left px-3 py-2">Invariants</th>
                <th className="text-left px-3 py-2">Corpus coverage</th>
                <th className="text-left px-3 py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {(telemetryQ.data ?? []).map((r) => (
                <tr key={r.run_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono">{r.project_id.slice(0, 8)}</td>
                  <td className="px-3 py-2">
                    <span className={
                      r.status === 'ok' ? 'text-emerald-600' : r.status === 'failed' ? 'text-red-600' : 'text-amber-600'
                    }>{r.status}{r.failed_stage ? ` (${r.failed_stage})` : ''}</span>
                  </td>
                  <td className="px-3 py-2">{fmtMs(r.total_ms)}</td>
                  <td className="px-3 py-2">{r.novelty_score ?? '—'}</td>
                  <td className="px-3 py-2">{r.overall_score ?? '—'}</td>
                  <td className="px-3 py-2">
                    {r.invariants_passed === null ? '—' : r.invariants_passed ? (
                      <CheckCircle2 size={14} className="text-emerald-500" />
                    ) : (
                      <XCircle size={14} className="text-red-500" />
                    )}
                  </td>
                  <td className="px-3 py-2">{fmtPct(r.corpus_key_coverage)}</td>
                  <td className="px-3 py-2 text-slate-400">{new Date(r.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
              {(telemetryQ.data ?? []).length === 0 && (
                <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-400">No submissions scored yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Ablation */}
      <section>
        <SectionHeader icon={<Activity size={18} />} title="Ablation — similarity channels"
          subtitle="semantic_only / graph_only / combined, where each exists yet" />
        {ablationQ.data && Object.keys(ablationQ.data.variants).length > 0 ? (
          <div className="grid md:grid-cols-3 gap-4">
            {Object.entries(ablationQ.data.variants).map(([variant, metricsList]) => (
              <div key={variant} className="border border-slate-200 rounded-xl p-4 bg-white">
                <div className="font-mono text-xs font-semibold text-[#1B2A4A] mb-2">{variant}</div>
                <div className="space-y-1.5">
                  {metricsList.map((m) => (
                    <div key={`${m.metric}:${m.slice}`} className="flex justify-between text-xs">
                      <span className="text-slate-500 truncate pr-2">{m.metric}</span>
                      <span className="font-medium">{fmtNum(m.value, 3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon={<Activity size={28} />} title="No ablation data yet" description="Only graph_only exists until the semantic channel ships." />
        )}
      </section>

      {/* Faculty agreement */}
      <section>
        <SectionHeader icon={<Users size={18} />} title="Faculty Agreement"
          subtitle={facultyQ.data?.note} />
        {facultyQ.data && facultyQ.data.metrics.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {facultyQ.data.metrics.map((m) => (
              <div key={m.metric} className="p-4 rounded-xl border bg-white">
                <div className="text-xs text-slate-500 truncate" title={m.metric}>{m.metric}</div>
                <div className="text-2xl font-bold mt-1">{fmtNum(m.value, 3)}</div>
                <div className="text-[11px] text-slate-400 mt-1">n={m.n ?? 0}</div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon={<Users size={28} />} title="No faculty evaluations recorded yet" />
        )}
      </section>

      {/* Recent runs */}
      <section>
        <SectionHeader icon={<Activity size={18} />} title="Recent Evaluation Runs" />
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="text-left px-3 py-2">Kind</th>
                <th className="text-left px-3 py-2">Trigger</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2">Cases</th>
                <th className="text-left px-3 py-2">Duration</th>
                <th className="text-left px-3 py-2">Started</th>
              </tr>
            </thead>
            <tbody>
              {(runsQ.data ?? []).map((r) => (
                <tr key={r.run_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-medium">{r.kind}</td>
                  <td className="px-3 py-2 text-slate-500">{r.trigger}</td>
                  <td className="px-3 py-2">
                    <span className={r.status === 'ok' ? 'text-emerald-600' : r.status === 'failed' ? 'text-red-600' : 'text-amber-600'}>{r.status}</span>
                  </td>
                  <td className="px-3 py-2">{r.n_cases ?? '—'}</td>
                  <td className="px-3 py-2">{fmtMs(r.duration_ms)}</td>
                  <td className="px-3 py-2 text-slate-400">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default QualityDashboard;
