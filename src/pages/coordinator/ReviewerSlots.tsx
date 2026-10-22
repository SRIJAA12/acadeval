import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getReviewerSlots, createReviewerSlot } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { UserCog, Plus, Info, Mail } from 'lucide-react';

const ReviewerSlots: React.FC = () => {
  const qc = useQueryClient();
  const [name, setName] = useState('');

  const { data: slots, isLoading, isError, refetch } = useQuery({
    queryKey: ['reviewerSlots'],
    queryFn: getReviewerSlots,
  });

  const createMutation = useMutation({
    mutationFn: (n: string) => createReviewerSlot(n),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['reviewerSlots'] }); setName(''); },
  });

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Reviewer Slots</h1>
        <p className="text-slate-500 mt-1">Pooled accounts (Reviewer 1, Reviewer 2, ...) that real staff log into during their assigned review window — no one types their own credentials.</p>
      </div>

      <div className="flex items-start gap-2 bg-indigo-50 border border-indigo-100 rounded-xl p-4 mb-6">
        <Info size={15} className="text-indigo-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-indigo-800">
          A slot's login password regenerates every time it's scheduled for a new review round, and is emailed to that round's
          real staff member automatically. The previous holder's access stops working immediately. Create slots here, then
          assign them to projects from <strong>Review Rounds</strong>.
        </p>
      </div>

      <div className="card mb-6">
        <h2 className="font-semibold text-navy-900 mb-3">Create Reviewer Slot</h2>
        <div className="flex gap-2">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            className="input"
            placeholder="e.g. Reviewer 1, Reviewer 2..."
          />
          <button
            onClick={() => name.trim() && createMutation.mutate(name.trim())}
            disabled={!name.trim() || createMutation.isPending}
            className="btn-primary flex-shrink-0"
          >
            <Plus size={16} /> Create Slot
          </button>
        </div>
      </div>

      <div className="card">
        {isLoading && <LoadingState message="Loading reviewer slots..." />}
        {isError && <ErrorState retry={refetch} />}
        {!isLoading && !isError && (!slots || slots.length === 0) && (
          <EmptyState icon={<UserCog size={28} />} title="No reviewer slots yet" description="Create one above to start scheduling review rounds." />
        )}
        {!isLoading && slots && slots.length > 0 && (
          <div className="space-y-2">
            {slots.map(s => (
              <div key={s.slotId} className="flex items-center justify-between bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center text-purple-700 font-bold text-sm">
                    {s.name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">{s.name}</p>
                    <p className="text-xs text-slate-400 flex items-center gap-1"><Mail size={11} />{s.email}</p>
                  </div>
                </div>
                <span className={`badge ${s.isActive ? 'badge-teal' : 'badge-slate'}`}>{s.isActive ? 'Active' : 'Inactive'}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewerSlots;
