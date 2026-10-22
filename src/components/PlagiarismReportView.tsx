import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPlagiarismReport, reviewPlagiarismMatch } from '../api/endpoints';
import { useAuth } from '../auth/AuthContext';
import { ErrorState } from './States';
import {
  ShieldAlert, ShieldCheck, FileText, Code2, Info, Loader2, ChevronDown, ChevronUp,
} from 'lucide-react';
import type { PlagiarismMatchItem, PlagiarismReviewStatus } from '../types';
import clsx from 'clsx';

const STATUS_CONFIG: Record<PlagiarismReviewStatus, { label: string; className: string }> = {
  unreviewed: { label: 'Awaiting Review', className: 'badge-gold' },
  confirmed: { label: 'Confirmed Plagiarism', className: 'badge-red' },
  acceptable_overlap: { label: 'Acceptable Overlap', className: 'badge-teal' },
  uncertain: { label: 'Uncertain', className: 'badge-orange' },
  no_issue: { label: 'No Issue', className: 'badge-slate' },
};

const REVIEW_OPTIONS: { value: Exclude<PlagiarismReviewStatus, 'unreviewed'>; label: string }[] = [
  { value: 'confirmed', label: 'Confirmed Plagiarism' },
  { value: 'acceptable_overlap', label: 'Acceptable Overlap (template/boilerplate/cited)' },
  { value: 'uncertain', label: 'Uncertain — needs discussion' },
  { value: 'no_issue', label: 'No Issue' },
];

const MatchCard: React.FC<{ match: PlagiarismMatchItem; projectId: string; canReview: boolean }> = ({ match, projectId, canReview }) => {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [status, setStatus] = useState<Exclude<PlagiarismReviewStatus, 'unreviewed'>>('acceptable_overlap');
  const [comment, setComment] = useState('');

  const reviewMutation = useMutation({
    mutationFn: () => reviewPlagiarismMatch(match.matchId, status, comment || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plagiarismReport', projectId] });
      setShowReviewForm(false);
    },
  });

  const statusCfg = STATUS_CONFIG[match.reviewStatus];

  return (
    <div className="border border-slate-100 rounded-xl overflow-hidden">
      <button onClick={() => setExpanded(v => !v)} className="w-full flex items-center justify-between gap-3 p-3 hover:bg-slate-50 text-left">
        <div className="flex items-center gap-2 min-w-0">
          {match.matchType === 'code' ? <Code2 size={15} className="text-indigo-500 flex-shrink-0" /> : <FileText size={15} className="text-teal-600 flex-shrink-0" />}
          <span className="text-sm font-medium text-slate-700 truncate">{match.sourceLabel}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs font-bold text-slate-500">{Math.round(match.score * 100)}%</span>
          <span className={clsx('badge text-[10px]', statusCfg.className)}>{statusCfg.label}</span>
          {expanded ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="p-3 border-t border-slate-100 bg-slate-50 space-y-3 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase mb-1">This Submission {match.candidateLocation && `· ${match.candidateLocation}`}</p>
              <p className="text-sm text-slate-700 bg-white rounded-lg p-2.5 border border-slate-100 whitespace-pre-wrap">{match.candidatePassage}</p>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase mb-1">Matched Source {match.sourceLocation && `· ${match.sourceLocation}`}</p>
              <p className="text-sm text-slate-700 bg-white rounded-lg p-2.5 border border-slate-100 whitespace-pre-wrap">{match.sourcePassage}</p>
            </div>
          </div>

          {match.reviewerComment && (
            <p className="text-xs text-slate-600 bg-white rounded-lg p-2 border border-slate-100">
              <strong>{match.reviewedByName}:</strong> {match.reviewerComment}
            </p>
          )}

          {canReview && (
            showReviewForm ? (
              <div className="space-y-2">
                <select value={status} onChange={e => setStatus(e.target.value as typeof status)} className="input text-sm">
                  {REVIEW_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <textarea value={comment} onChange={e => setComment(e.target.value)} rows={2} className="input text-sm resize-none" placeholder="Optional note..." />
                <div className="flex gap-2">
                  <button onClick={() => reviewMutation.mutate()} disabled={reviewMutation.isPending} className="btn-primary text-xs py-1.5">
                    {reviewMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : null} Save Decision
                  </button>
                  <button onClick={() => setShowReviewForm(false)} className="btn-outline text-xs py-1.5">Cancel</button>
                </div>
              </div>
            ) : (
              <button onClick={() => setShowReviewForm(true)} className="btn-outline text-xs py-1.5">Set Review Decision</button>
            )
          )}
        </div>
      )}
    </div>
  );
};

const PlagiarismReportView: React.FC<{ projectId: string }> = ({ projectId }) => {
  const { user } = useAuth();
  const canReview = user?.role === 'guide' || user?.role === 'reviewer' || user?.role === 'hod';

  const { data: report, isLoading, isError, refetch } = useQuery({
    queryKey: ['plagiarismReport', projectId],
    queryFn: () => getPlagiarismReport(projectId),
    enabled: !!projectId,
  });

  if (isLoading) return <div className="card animate-pulse h-24" />;
  if (isError || !report) return <ErrorState retry={refetch} />;

  const hasMatches = report.matches.length > 0;

  return (
    <div className="card">
      <h2 className="text-base font-semibold text-navy-900 mb-1 flex items-center gap-2">
        {hasMatches ? <ShieldAlert size={18} className="text-gold-500" /> : <ShieldCheck size={18} className="text-teal-500" />}
        Plagiarism Report
      </h2>
      <p className="text-xs text-slate-400 mb-3">TF-IDF text passage matching against other submitted projects, plus code fingerprint matching against linked GitHub repos.</p>

      <div className="flex items-start gap-2 bg-indigo-50 border border-indigo-100 rounded-xl p-3 mb-4">
        <Info size={14} className="text-indigo-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-indigo-900">{report.summaryText}</p>
      </div>

      {report.codeFetchError && (
        <p className="text-xs text-slate-400 mb-3">Code check note: {report.codeFetchError}</p>
      )}

      {hasMatches && (
        <div className="flex gap-3 mb-4">
          <span className="badge badge-slate text-[11px]">Text: {Math.round(report.textMax * 100)}% max · {report.textMatchCount} match(es)</span>
          <span className="badge badge-slate text-[11px]">Code: {Math.round(report.codeMax * 100)}% max · {report.codeMatchCount} match(es)</span>
        </div>
      )}

      {hasMatches && (
        <div className="space-y-2">
          {report.matches.map(m => (
            <MatchCard key={m.matchId} match={m} projectId={projectId} canReview={canReview} />
          ))}
        </div>
      )}
    </div>
  );
};

export default PlagiarismReportView;
