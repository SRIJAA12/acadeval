import React, { useRef, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Target, Sparkles, ChevronDown, ChevronUp, Send, Loader2, Lightbulb, AlertTriangle,
  CheckCircle2, Trophy, MessageCircle, Eye,
} from 'lucide-react';
import clsx from 'clsx';
import { getScoreCoach, askScoreCoach } from '../api/endpoints';
import { LoadingState, ErrorState } from './States';
import type { CoachAnswer, CoachDimension, CoachStatus } from '../types';

const STATUS_STYLE: Record<CoachStatus, { bar: string; text: string; label: string }> = {
  strong: { bar: 'bg-teal-500', text: 'text-teal-700', label: 'Strong' },
  fair: { bar: 'bg-gold-500', text: 'text-gold-700', label: 'Fair' },
  low: { bar: 'bg-red-500', text: 'text-red-700', label: 'Needs work' },
  not_scored: { bar: 'bg-slate-300', text: 'text-slate-500', label: 'Not scored' },
};

const SUGGESTIONS = [
  'Why is my score low?',
  'What should I fix first?',
  'What do I need for a 100% score?',
  'How can I reach the next grade?',
];

interface ChatTurn {
  question: string;
  answer?: CoachAnswer;
  error?: string;
}

const DimensionRow: React.FC<{
  dim: CoachDimension;
  open: boolean;
  onToggle: () => void;
  onAsk?: (dim: CoachDimension) => void;
}> = ({ dim, open, onToggle, onAsk }) => {
  const st = STATUS_STYLE[dim.status];
  const pct = dim.score ?? 0;
  return (
    <div id={`coach-dim-${dim.key}`} className="border border-slate-100 rounded-xl overflow-hidden">
      <button onClick={onToggle} className="w-full flex items-center gap-3 p-3 text-left hover:bg-slate-50">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-sm font-semibold text-slate-800">
              {dim.name} <span className="text-xs font-normal text-slate-400">· {dim.weight_percent}% of total</span>
            </span>
            <span className="flex items-center gap-2 flex-shrink-0">
              {dim.points_recoverable >= 0.5 && (
                <span className="text-[11px] font-medium text-teal-700 bg-teal-50 border border-teal-100 rounded-full px-2 py-0.5">
                  up to +{dim.points_recoverable} pts
                </span>
              )}
              <span className={clsx('text-sm font-bold', st.text)}>
                {dim.score === null ? '—' : dim.score.toFixed(0)}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </span>
            </span>
          </div>
          <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
            <div className={clsx('h-full rounded-full', st.bar)} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
          </div>
        </div>
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>

      {open && (
        <div className="border-t border-slate-100 bg-slate-50/60 p-4 space-y-4 animate-fade-in">
          <section>
            <h4 className="text-xs font-semibold uppercase text-slate-500 mb-1.5 flex items-center gap-1.5">
              <Eye size={13} /> Why this score
            </h4>
            <ul className="space-y-1">
              {dim.why.map((w, i) => (
                <li key={i} className="text-sm text-slate-700 flex gap-2"><span className="text-slate-300">•</span>{w}</li>
              ))}
            </ul>
          </section>

          {dim.gaps.length > 0 && (
            <section>
              <h4 className="text-xs font-semibold uppercase text-amber-700 mb-1.5 flex items-center gap-1.5">
                <AlertTriangle size={13} /> Gaps holding it back
              </h4>
              <ul className="space-y-1">
                {dim.gaps.map((g, i) => (
                  <li key={i} className="text-sm text-slate-700 flex gap-2"><span className="text-amber-400">•</span>{g}</li>
                ))}
              </ul>
            </section>
          )}

          {dim.actions.length > 0 && (
            <section>
              <h4 className="text-xs font-semibold uppercase text-teal-700 mb-1.5 flex items-center gap-1.5">
                <Lightbulb size={13} /> How to improve
              </h4>
              <ol className="space-y-2">
                {dim.actions.map((a, i) => (
                  <li key={i} className="text-sm text-slate-700 flex gap-2.5">
                    <span className="w-5 h-5 rounded-full bg-teal-500 text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                    <span className="flex-1">
                      {a.text}
                      {a.points > 0 && <span className="ml-1.5 text-xs font-medium text-teal-700">(up to +{a.points} pts)</span>}
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {dim.criteria.length > 0 && (
            <section>
              <h4 className="text-xs font-semibold uppercase text-slate-500 mb-1.5">Criteria breakdown</h4>
              <div className="space-y-1.5">
                {dim.criteria.map(c => (
                  <div key={c.key} className="bg-white border border-slate-100 rounded-lg p-2.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700">{c.name}</span>
                      <span className={clsx('font-bold', STATUS_STYLE[c.status].text)}>
                        {c.score.toFixed(0)}
                        <span className="text-xs font-normal text-slate-400"> / {c.max_reachable.toFixed(0)} max</span>
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{c.standard}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="bg-white border border-teal-100 rounded-xl p-3">
            <h4 className="text-xs font-semibold uppercase text-teal-700 mb-1.5 flex items-center gap-1.5">
              <Trophy size={13} /> What a 100% score looks like
            </h4>
            <ul className="space-y-1">
              {dim.standard_for_100.map((s, i) => (
                <li key={i} className="text-sm text-slate-700 flex gap-2">
                  <CheckCircle2 size={14} className="text-teal-500 mt-0.5 flex-shrink-0" />{s}
                </li>
              ))}
            </ul>
            {dim.note && <p className="text-xs text-slate-500 mt-2 italic">{dim.note}</p>}
          </section>

          {onAsk && (
            <button onClick={() => onAsk(dim)} className="btn-outline text-xs py-1.5 flex items-center gap-1.5">
              <MessageCircle size={13} /> Ask about {dim.name}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

interface Props {
  projectId: string;
  /** Students can ask questions; guides, reviewers and HOD get a read-only view. */
  canAsk?: boolean;
}

const ScoreCoachPanel: React.FC<Props> = ({ projectId, canAsk = false }) => {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['scoreCoach', projectId],
    queryFn: () => getScoreCoach(projectId),
    enabled: !!projectId,
    retry: false,
  });

  const [openKey, setOpenKey] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [focusKey, setFocusKey] = useState<string | undefined>(undefined);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const askRef = useRef<HTMLTextAreaElement>(null);

  const ask = useMutation({
    mutationFn: ({ q, dim }: { q: string; dim?: string }) => askScoreCoach(projectId, q, dim),
  });

  const submit = (q: string, dim?: string) => {
    const text = q.trim();
    if (text.length < 3 || ask.isPending) return;
    setTurns(t => [...t, { question: text }]);
    setQuestion('');
    ask.mutate({ q: text, dim }, {
      onSuccess: answer => setTurns(t => t.map((x, i) => (i === t.length - 1 ? { ...x, answer } : x))),
      onError: (err: any) => {
        const detail = err?.response?.data?.detail;
        setTurns(t => t.map((x, i) => (i === t.length - 1 ? { ...x, error: typeof detail === 'string' ? detail : 'Could not get an answer. Please try again.' } : x)));
      },
    });
  };

  const jumpTo = (key: string) => {
    setOpenKey(key);
    setTimeout(() => document.getElementById(`coach-dim-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50);
  };

  const askAbout = (dim: CoachDimension) => {
    setFocusKey(dim.key);
    setQuestion(`How do I improve my ${dim.name} score?`);
    askRef.current?.focus();
  };

  if (isLoading) return <div className="card"><LoadingState message="Loading score coach..." /></div>;
  if (isError || !data) return <div className="card"><ErrorState retry={refetch} /></div>;
  if (!data.available) {
    return (
      <div className="card">
        <h2 className="text-base font-semibold text-navy-900 mb-1 flex items-center gap-2"><Target size={18} className="text-teal-500" /> Score Coach</h2>
        <p className="text-sm text-slate-500">{data.message ?? 'Your evaluation is not ready yet. Check back once processing finishes.'}</p>
      </div>
    );
  }

  const overall = data.overall_score ?? 0;
  const next = data.next_grade;
  const nextProgress = next ? Math.max(0, Math.min(100, (overall / next.threshold) * 100)) : 100;

  return (
    <div className="card space-y-5">
      <div>
        <h2 className="text-base font-semibold text-navy-900 mb-1 flex items-center gap-2">
          <Target size={18} className="text-teal-500" /> Score Coach
        </h2>
        <p className="text-xs text-slate-400">
          {canAsk
            ? 'Why you got each score, what is missing, how to improve it, and what 100% requires.'
            : 'Read-only view of the coaching the student sees: why each score was given and how to improve it.'}
        </p>
      </div>

      <div className="rounded-xl bg-navy-50 border border-navy-100 p-4">
        <p className="text-sm text-navy-900">{data.summary}</p>
        <div className="mt-3">
          <div className="flex justify-between text-[11px] text-slate-500 mb-1">
            <span>Current {overall.toFixed(1)}</span>
            <span>{next ? `Next: grade ${next.grade} at ${next.threshold}` : 'Top grade reached'}</span>
          </div>
          <div className="h-2.5 rounded-full bg-white overflow-hidden border border-navy-100">
            <div className="h-full bg-teal-500 rounded-full" style={{ width: `${nextProgress}%` }} />
          </div>
          {data.max_overall_reachable !== undefined && data.max_overall_reachable < 100 && (
            <p className="text-[11px] text-slate-500 mt-1.5">
              Under the current rubric the highest reachable overall score is about {data.max_overall_reachable}, because some criteria are capped.
            </p>
          )}
        </div>
      </div>

      {data.priorities.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-1.5">
            <Sparkles size={15} className="text-gold-500" /> Where to start
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {data.priorities.slice(0, 3).map((p, i) => (
              <button key={p.dimension_key} onClick={() => jumpTo(p.dimension_key)}
                className="text-left rounded-xl border border-slate-100 hover:border-teal-300 bg-white p-3 transition">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-slate-500">#{i + 1}</span>
                  <span className="text-[11px] font-medium text-teal-700 bg-teal-50 rounded-full px-2 py-0.5">up to +{p.points_recoverable} pts</span>
                </div>
                <p className="text-sm font-semibold text-slate-800">{p.name}</p>
                <p className="text-xs text-slate-500 mt-1 line-clamp-3">{p.top_action}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Every dimension, explained</h3>
        <div className="space-y-2">
          {data.dimensions.map(d => (
            <DimensionRow key={d.key} dim={d} open={openKey === d.key}
              onToggle={() => setOpenKey(openKey === d.key ? null : d.key)}
              onAsk={canAsk ? askAbout : undefined} />
          ))}
        </div>
      </div>

      {canAsk && (
        <div className="rounded-xl border border-slate-200 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
            <MessageCircle size={15} className="text-teal-500" /> Ask the Score Coach
          </h3>

          {turns.length > 0 && (
            <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {turns.map((t, i) => (
                <div key={i} className="space-y-1.5">
                  <div className="ml-auto max-w-[85%] bg-teal-600 text-white text-sm rounded-2xl rounded-br-sm px-3 py-2 w-fit">{t.question}</div>
                  {t.answer && (
                    <div className="max-w-[92%] bg-slate-50 border border-slate-100 rounded-2xl rounded-bl-sm px-3 py-2">
                      <p className="text-sm text-slate-800 whitespace-pre-wrap">{t.answer.answer}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className={clsx('text-[10px] font-medium rounded-full px-2 py-0.5',
                          t.answer.source === 'ai' ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-500')}>
                          {t.answer.source === 'ai' ? 'AI answer' : 'Rule-based answer'}
                        </span>
                        {t.answer.relatedDimensions.map(k => (
                          <button key={k} onClick={() => jumpTo(k)} className="text-[11px] text-teal-700 underline">
                            {data.dimensions.find(d => d.key === k)?.name ?? k}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {t.error && <p className="text-xs text-red-600">{t.error}</p>}
                  {!t.answer && !t.error && (
                    <div className="flex items-center gap-2 text-xs text-slate-400"><Loader2 size={12} className="animate-spin" /> Thinking…</div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-1.5">
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => submit(s)} disabled={ask.isPending}
                className="text-xs rounded-full border border-slate-200 px-2.5 py-1 text-slate-600 hover:border-teal-300 hover:text-teal-700 disabled:opacity-50">
                {s}
              </button>
            ))}
          </div>

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              {focusKey && (
                <p className="text-[11px] text-slate-500 mb-1">
                  Focused on {data.dimensions.find(d => d.key === focusKey)?.name}{' '}
                  <button className="underline" onClick={() => setFocusKey(undefined)}>clear</button>
                </p>
              )}
              <textarea
                ref={askRef}
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(question, focusKey); } }}
                rows={2}
                maxLength={500}
                className="input text-sm resize-none"
                placeholder="e.g. Why is my technical depth low, and what exactly should I add?"
              />
            </div>
            <button onClick={() => submit(question, focusKey)} disabled={ask.isPending || question.trim().length < 3}
              className="btn-primary px-3 py-2.5" aria-label="Send question">
              {ask.isPending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>
      )}

      {data.disclaimer && <p className="text-[11px] text-slate-400">{data.disclaimer}</p>}
    </div>
  );
};

export default ScoreCoachPanel;
