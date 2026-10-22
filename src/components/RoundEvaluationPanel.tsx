import React, { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRoundEvaluations, updateRoundEvaluation, publishRoundEvaluation } from '../api/endpoints';
import { useAuth } from '../auth/AuthContext';
import { CalendarClock, Save, Send, CheckCircle, Trophy, Info } from 'lucide-react';
import type { RoundEvaluationItem } from '../types';
import clsx from 'clsx';

interface Props {
  projectId: string;
}

const DIMENSIONS: { key: keyof RoundEvaluationItem & string; label: string }[] = [
  { key: 'novelty', label: 'Novelty' },
  { key: 'feasibility', label: 'Feasibility' },
  { key: 'completeness', label: 'Completeness' },
  { key: 'technicalDepth', label: 'Technical Depth' },
  { key: 'clarity', label: 'Clarity' },
  { key: 'similarityRisk', label: 'Similarity Risk' },
  { key: 'publicationPotential', label: 'Publication Potential' },
];

const RoundCard: React.FC<{ evaluation: RoundEvaluationItem; projectId: string; editable: boolean }> = ({ evaluation, projectId, editable }) => {
  const qc = useQueryClient();
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comment, setComment] = useState(evaluation.comment);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!dirty) {
      const initial: Record<string, number> = {};
      DIMENSIONS.forEach(d => { initial[d.key] = (evaluation[d.key] as number | null) ?? 70; });
      setScores(initial);
      setComment(evaluation.comment);
    }
  }, [evaluation, dirty]);

  const saveMutation = useMutation({
    mutationFn: () => updateRoundEvaluation(projectId, evaluation.roundId, {
      novelty: scores.novelty, feasibility: scores.feasibility, completeness: scores.completeness,
      technicalDepth: scores.technicalDepth, clarity: scores.clarity, similarityRisk: scores.similarityRisk,
      publicationPotential: scores.publicationPotential, comment,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['roundEvaluations', projectId] }); setDirty(false); },
  });

  const publishMutation = useMutation({
    mutationFn: () => publishRoundEvaluation(projectId, evaluation.roundId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roundEvaluations', projectId] }),
  });

  const canEdit = editable && !evaluation.isPublished;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CalendarClock size={16} className="text-indigo-500" />
          <h3 className="font-semibold text-navy-900">{evaluation.roundName}</h3>
          {evaluation.isFinalRound && <span className="badge badge-gold"><Trophy size={11} /> Final</span>}
        </div>
        {evaluation.isPublished ? (
          <span className="badge badge-teal"><CheckCircle size={11} /> Published</span>
        ) : (
          <span className="badge badge-slate">Draft</span>
        )}
      </div>

      {canEdit ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {DIMENSIONS.map(d => (
              <div key={d.key}>
                <label className="label text-xs">{d.label}</label>
                <div className="flex items-center gap-2">
                  <input
                    type="range" min={0} max={100} value={scores[d.key] ?? 70}
                    onChange={e => { setScores(prev => ({ ...prev, [d.key]: Number(e.target.value) })); setDirty(true); }}
                    className="flex-1 accent-indigo-500"
                  />
                  <span className="w-8 text-right text-sm font-semibold text-navy-900">{scores[d.key] ?? 70}</span>
                </div>
              </div>
            ))}
          </div>
          <div>
            <label className="label text-xs">Comment for the student</label>
            <textarea
              value={comment}
              onChange={e => { setComment(e.target.value); setDirty(true); }}
              rows={2}
              className="input text-sm resize-none"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="btn-outline text-sm">
              <Save size={13} /> Save Draft
            </button>
            <button onClick={() => publishMutation.mutate()} disabled={publishMutation.isPending} className="btn-primary text-sm">
              <Send size={13} /> Publish{evaluation.isFinalRound ? ' Final Grade' : ' Round Result'}
            </button>
          </div>
        </div>
      ) : (
        <div>
          {evaluation.overallScore !== null ? (
            <div className="flex items-center gap-3">
              <div className={clsx(
                'w-12 h-12 rounded-xl flex items-center justify-center font-display font-bold',
                evaluation.overallScore >= 80 ? 'bg-teal-50 text-teal-700' :
                evaluation.overallScore >= 60 ? 'bg-gold-50 text-gold-700' : 'bg-red-50 text-red-700'
              )}>
                {Math.round(evaluation.overallScore)}
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">{evaluation.grade}</p>
                <p className="text-xs text-slate-400">By {evaluation.reviewerSlotName}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Not yet scored.</p>
          )}
          {evaluation.comment && <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3 border border-slate-100 mt-2">{evaluation.comment}</p>}
          {!editable && !evaluation.isPublished && (
            <p className="text-xs text-slate-400 mt-2 flex items-center gap-1"><Info size={11} /> Awaiting the assigned reviewer.</p>
          )}
        </div>
      )}
    </div>
  );
};

const RoundEvaluationPanel: React.FC<Props> = ({ projectId }) => {
  const { user } = useAuth();
  const { data: evaluations, isLoading } = useQuery({
    queryKey: ['roundEvaluations', projectId],
    queryFn: () => getRoundEvaluations(projectId),
    enabled: !!projectId,
  });

  if (isLoading) return <div className="card animate-pulse h-24" />;
  if (!evaluations || evaluations.length === 0) {
    return (
      <div className="card flex items-start gap-2">
        <Info size={15} className="text-slate-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-500">No review rounds have been scheduled for this project yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {evaluations.map(ev => (
        <RoundCard
          key={ev.evaluationId}
          evaluation={ev}
          projectId={projectId}
          editable={user?.role === 'hod' || (user?.role === 'reviewer' && user?.name === ev.reviewerSlotName)}
        />
      ))}
    </div>
  );
};

export default RoundEvaluationPanel;
