import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getReviewRounds, createReviewRound } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { CalendarClock, Plus, ArrowRight, Trophy } from 'lucide-react';
import clsx from 'clsx';

const ReviewRounds: React.FC = () => {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [isFinal, setIsFinal] = useState(false);

  const { data: rounds, isLoading, isError, refetch } = useQuery({
    queryKey: ['reviewRounds'],
    queryFn: getReviewRounds,
  });

  const createMutation = useMutation({
    mutationFn: () => createReviewRound({
      name, description: description || undefined, scheduledDate: scheduledDate || undefined, isFinal,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reviewRounds'] });
      setShowForm(false); setName(''); setDescription(''); setScheduledDate(''); setIsFinal(false);
    },
  });

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900">Review Rounds</h1>
          <p className="text-slate-500 mt-1">Schedule each review round (Review 1, Review 2, Final Review...) — each round gets its own independent score.</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="btn-primary flex-shrink-0">
          <Plus size={16} /> New Round
        </button>
      </div>

      {showForm && (
        <div className="card mb-6 space-y-4 animate-fade-in">
          <h2 className="font-semibold text-navy-900">Create Review Round</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Round Name *</label>
              <input value={name} onChange={e => setName(e.target.value)} className="input" placeholder="e.g. Review 1" />
            </div>
            <div>
              <label className="label">Scheduled Date</label>
              <input type="date" value={scheduledDate} onChange={e => setScheduledDate(e.target.value)} className="input" />
            </div>
          </div>
          <div>
            <label className="label">Description</label>
            <input value={description} onChange={e => setDescription(e.target.value)} className="input" placeholder="Optional notes about this round" />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={isFinal} onChange={e => setIsFinal(e.target.checked)} className="w-4 h-4 accent-indigo-500" />
            This is the final round — its published score becomes each project's official evaluation
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate()}
              disabled={!name.trim() || createMutation.isPending}
              className="btn-primary"
            >
              Create Round
            </button>
            <button onClick={() => setShowForm(false)} className="btn-outline">Cancel</button>
          </div>
        </div>
      )}

      {isLoading && <LoadingState message="Loading review rounds..." />}
      {isError && <ErrorState retry={refetch} />}
      {!isLoading && !isError && (!rounds || rounds.length === 0) && (
        <EmptyState icon={<CalendarClock size={28} />} title="No review rounds yet" description="Create one to start scheduling reviewer assignments." />
      )}
      {!isLoading && rounds && rounds.length > 0 && (
        <div className="space-y-3">
          {rounds.map(r => (
            <Link key={r.roundId} to={`/coordinator/review-rounds/${r.roundId}`} className="card flex items-center justify-between hover:shadow-md transition-shadow block">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-navy-900">{r.name}</h3>
                  {r.isFinal && <span className="badge badge-gold"><Trophy size={11} /> Final</span>}
                </div>
                {r.description && <p className="text-sm text-slate-500">{r.description}</p>}
                <p className="text-xs text-slate-400 mt-1">
                  {r.scheduledDate ? new Date(r.scheduledDate).toLocaleDateString('en-IN') : 'No date set'}
                  {' · '}{r.assignmentCount} assigned · {r.publishedCount} published
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={clsx('badge', r.publishedCount >= r.assignmentCount && r.assignmentCount > 0 ? 'badge-teal' : 'badge-slate')}>
                  {r.assignmentCount === 0 ? 'Not scheduled' : r.publishedCount >= r.assignmentCount ? 'Complete' : 'In progress'}
                </span>
                <ArrowRight size={16} className="text-slate-300" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReviewRounds;
