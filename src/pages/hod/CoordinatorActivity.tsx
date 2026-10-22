import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCoordinatorOverview, getRoster, getReviewerSlots, getReviewRounds } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import {
  FolderGit2, UserX, Hourglass, UserCog, CalendarClock, Scale, Eye,
} from 'lucide-react';
import clsx from 'clsx';

const CoordinatorActivity: React.FC = () => {
  const overviewQuery = useQuery({ queryKey: ['coordinatorOverview'], queryFn: getCoordinatorOverview });
  const rosterQuery = useQuery({ queryKey: ['roster'], queryFn: getRoster });
  const slotsQuery = useQuery({ queryKey: ['reviewerSlots'], queryFn: getReviewerSlots });
  const roundsQuery = useQuery({ queryKey: ['reviewRounds'], queryFn: getReviewRounds });

  if (overviewQuery.isLoading) return <LoadingState message="Loading coordinator activity..." />;
  if (overviewQuery.isError || !overviewQuery.data) return <ErrorState retry={overviewQuery.refetch} />;

  const o = overviewQuery.data;
  const pendingErrors = (rosterQuery.data || []).filter(r => r.error);

  return (
    <div>
      <div className="mb-8 flex items-center gap-2">
        <Eye size={20} className="text-slate-400" />
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900">Coordinator Activity</h1>
          <p className="text-slate-500 mt-1">Read-only oversight of allocation, reviewer scheduling, and rubrics. The coordinator operates this; you monitor it.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Total Projects', value: o.totalProjects, icon: <FolderGit2 size={18} />, tone: 'bg-navy-50 text-navy-900' },
          { label: 'Unallocated', value: o.unallocatedProjects, icon: <UserX size={18} />, tone: o.unallocatedProjects > 0 ? 'bg-red-50 text-red-700' : 'bg-teal-50 text-teal-700' },
          { label: 'Pending Roster Rows', value: o.pendingRosterRows, icon: <Hourglass size={18} />, tone: o.pendingRosterRows > 0 ? 'bg-gold-50 text-gold-700' : 'bg-teal-50 text-teal-700' },
          { label: 'Reviewer Slots', value: o.reviewerSlotCount, icon: <UserCog size={18} />, tone: 'bg-purple-50 text-purple-700' },
          { label: 'Review Rounds', value: o.activeRoundCount, icon: <CalendarClock size={18} />, tone: 'bg-indigo-50 text-indigo-700' },
          { label: 'Rubrics Pending Approval', value: o.rubricsPendingApproval, icon: <Scale size={18} />, tone: o.rubricsPendingApproval > 0 ? 'bg-gold-50 text-gold-700' : 'bg-teal-50 text-teal-700' },
        ].map(c => (
          <div key={c.label} className="card">
            <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center', c.tone)}>{c.icon}</div>
            <p className="text-2xl font-display font-bold text-navy-900 mt-3">{c.value}</p>
            <p className="text-sm text-slate-500">{c.label}</p>
          </div>
        ))}
      </div>

      {o.rubricsPendingApproval > 0 && (
        <div className="card mb-6 flex items-center justify-between bg-gold-50 border-gold-200">
          <p className="text-sm text-gold-800">{o.rubricsPendingApproval} rubric{o.rubricsPendingApproval !== 1 ? 's' : ''} awaiting your approval.</p>
          <Link to="/hod/rubrics" className="btn-primary">Review Rubrics</Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <h2 className="font-semibold text-navy-900 mb-3">Review Rounds</h2>
          {roundsQuery.isLoading && <p className="text-sm text-slate-400">Loading...</p>}
          {!roundsQuery.isLoading && (!roundsQuery.data || roundsQuery.data.length === 0) && (
            <p className="text-sm text-slate-400">No review rounds scheduled yet.</p>
          )}
          <div className="space-y-2">
            {(roundsQuery.data || []).map(r => (
              <div key={r.roundId} className="flex items-center justify-between bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div>
                  <p className="font-medium text-slate-700 text-sm">{r.name}{r.isFinal && <span className="badge badge-gold ml-2 text-[9px]">Final</span>}</p>
                  <p className="text-xs text-slate-400">{r.assignmentCount} assigned · {r.publishedCount} published</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="font-semibold text-navy-900 mb-3">Reviewer Slots</h2>
          {slotsQuery.isLoading && <p className="text-sm text-slate-400">Loading...</p>}
          {!slotsQuery.isLoading && (!slotsQuery.data || slotsQuery.data.length === 0) && (
            <p className="text-sm text-slate-400">No reviewer slots created yet.</p>
          )}
          <div className="space-y-2">
            {(slotsQuery.data || []).map(s => (
              <div key={s.slotId} className="flex items-center justify-between bg-slate-50 rounded-xl p-3 border border-slate-100">
                <span className="font-medium text-slate-700 text-sm">{s.name}</span>
                <span className="text-xs text-slate-400">{s.email}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {pendingErrors.length > 0 && (
        <div className="card mt-5 border-red-200">
          <h2 className="font-semibold text-red-700 mb-3">Roster Rows With Errors</h2>
          <div className="space-y-2">
            {pendingErrors.map(r => (
              <div key={r.allocationId} className="flex items-center justify-between bg-red-50 rounded-xl p-3 border border-red-100 text-sm">
                <span className="font-medium text-slate-700">{r.rollNo}</span>
                <span className="text-red-600">{r.error}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CoordinatorActivity;
