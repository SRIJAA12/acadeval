import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCoordinatorOverview } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import {
  FolderGit2, UserX, Hourglass, UserCog, CalendarClock, Scale, ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';

const CoordinatorOverview: React.FC = () => {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['coordinatorOverview'],
    queryFn: getCoordinatorOverview,
  });

  if (isLoading) return <LoadingState message="Loading coordinator overview..." />;
  if (isError || !data) return <ErrorState retry={refetch} />;

  const cards = [
    {
      label: 'Total Projects', value: data.totalProjects, icon: <FolderGit2 size={20} />,
      tone: 'bg-navy-50 text-navy-900', to: null,
    },
    {
      label: 'Unallocated (No Guide)', value: data.unallocatedProjects, icon: <UserX size={20} />,
      tone: data.unallocatedProjects > 0 ? 'bg-red-50 text-red-700' : 'bg-teal-50 text-teal-700', to: '/coordinator/roster',
    },
    {
      label: 'Pending Roster Rows', value: data.pendingRosterRows, icon: <Hourglass size={20} />,
      tone: data.pendingRosterRows > 0 ? 'bg-gold-50 text-gold-700' : 'bg-teal-50 text-teal-700', to: '/coordinator/roster',
    },
    {
      label: 'Reviewer Slots', value: data.reviewerSlotCount, icon: <UserCog size={20} />,
      tone: 'bg-purple-50 text-purple-700', to: '/coordinator/reviewer-slots',
    },
    {
      label: 'Review Rounds', value: data.activeRoundCount, icon: <CalendarClock size={20} />,
      tone: 'bg-indigo-50 text-indigo-700', to: '/coordinator/review-rounds',
    },
    {
      label: 'Rubrics Pending HOD Approval', value: data.rubricsPendingApproval, icon: <Scale size={20} />,
      tone: data.rubricsPendingApproval > 0 ? 'bg-gold-50 text-gold-700' : 'bg-teal-50 text-teal-700', to: '/coordinator/rubrics',
    },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Coordinator Overview</h1>
        <p className="text-slate-500 mt-1">Allocate guides &amp; teams, schedule reviewer slots, and set rubrics. The HOD monitors this from their own dashboard.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map(c => {
          const inner = (
            <div className="card hover:shadow-md transition-shadow h-full">
              <div className="flex items-start justify-between">
                <div className={clsx('w-11 h-11 rounded-xl flex items-center justify-center', c.tone)}>{c.icon}</div>
                {c.to && <ArrowRight size={16} className="text-slate-300" />}
              </div>
              <p className="text-3xl font-display font-bold text-navy-900 mt-4">{c.value}</p>
              <p className="text-sm text-slate-500 mt-1">{c.label}</p>
            </div>
          );
          return c.to ? <Link key={c.label} to={c.to}>{inner}</Link> : <div key={c.label}>{inner}</div>;
        })}
      </div>
    </div>
  );
};

export default CoordinatorOverview;
