import React, { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getGuideFeedback, updateGuideFeedback } from '../api/endpoints';
import { MessageCircle, Save, Info } from 'lucide-react';
import clsx from 'clsx';

interface Props {
  projectId: string;
  /** True on the guide's own view of their assigned project — shows the edit form. */
  editable: boolean;
}

const GuideFeedbackPanel: React.FC<Props> = ({ projectId, editable }) => {
  const qc = useQueryClient();
  const { data: feedback, isLoading } = useQuery({
    queryKey: ['guideFeedback', projectId],
    queryFn: () => getGuideFeedback(projectId),
    enabled: !!projectId,
  });

  const [score, setScore] = useState(70);
  const [comment, setComment] = useState('');
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (feedback && !dirty) {
      setScore(feedback.overallScore);
      setComment(feedback.comment);
    }
  }, [feedback, dirty]);

  const saveMutation = useMutation({
    mutationFn: () => updateGuideFeedback(projectId, score, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['guideFeedback', projectId] });
      setDirty(false);
    },
  });

  if (isLoading) return <div className="card animate-pulse h-32" />;

  return (
    <div className="card">
      <h2 className="text-base font-semibold text-navy-900 mb-1 flex items-center gap-2">
        <MessageCircle size={18} className="text-gold-500" /> Guide's Feedback
      </h2>
      <div className="flex items-start gap-2 bg-gold-50 border border-gold-100 rounded-xl p-3 mb-4">
        <Info size={14} className="text-gold-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-gold-800">
          This is the guide's informal read on the work so far — meant to help the student improve.
          It is <strong>not the official grade</strong>; the final score comes from the reviewer.
        </p>
      </div>

      {editable ? (
        <div className="space-y-3">
          <div>
            <label className="label">Informal Mark</label>
            <div className="flex items-center gap-3">
              <input
                type="range" min={0} max={100} value={score}
                onChange={e => { setScore(Number(e.target.value)); setDirty(true); }}
                className="flex-1 accent-gold-500"
              />
              <span className="w-12 text-right font-bold text-navy-900">{score}</span>
            </div>
          </div>
          <div>
            <label className="label">Comments for the student</label>
            <textarea
              value={comment}
              onChange={e => { setComment(e.target.value); setDirty(true); }}
              rows={3}
              className="input text-sm resize-none"
              placeholder="What's working, what needs more depth, what to focus on next..."
            />
          </div>
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="btn-primary text-sm"
          >
            <Save size={14} /> {feedback ? 'Update Feedback' : 'Share Feedback'}
          </button>
          {feedback && (
            <p className="text-[11px] text-slate-400">Last updated {new Date(feedback.updatedAt).toLocaleString()}</p>
          )}
        </div>
      ) : feedback ? (
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className={clsx(
              'w-14 h-14 rounded-2xl flex items-center justify-center font-display font-bold text-xl',
              feedback.overallScore >= 80 ? 'bg-teal-50 text-teal-700' :
              feedback.overallScore >= 60 ? 'bg-gold-50 text-gold-700' : 'bg-red-50 text-red-700'
            )}>
              {feedback.overallScore}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700">{feedback.guideName}</p>
              <p className="text-[11px] text-slate-400">{new Date(feedback.updatedAt).toLocaleString()}</p>
            </div>
          </div>
          {feedback.comment && <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3 border border-slate-100">{feedback.comment}</p>}
        </div>
      ) : (
        <p className="text-sm text-slate-400 text-center py-4">Your guide hasn't shared feedback yet.</p>
      )}
    </div>
  );
};

export default GuideFeedbackPanel;
