import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMyTeams } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { Users, ChevronRight, Crown } from 'lucide-react';

const TeamProgress: React.FC = () => {
  const navigate = useNavigate();
  const { data: teams, isLoading, isError, refetch } = useQuery({
    queryKey: ['myTeams'],
    queryFn: getMyTeams,
  });

  if (isLoading) return <LoadingState message="Loading your teams..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Team Progress</h1>
        <p className="text-slate-500 mt-1">Every team you're in, allocated by your coordinator — discuss, assign tasks, and track progress together.</p>
      </div>

      {!teams?.length ? (
        <EmptyState
          icon={<Users size={28} />}
          title="You're not on a team yet"
          description="Your coordinator allocates teams via the roster upload. Once you're added to one, it will appear here."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {teams.map(team => (
            <div
              key={team.teamId}
              onClick={() => navigate(`/student/team-progress/${team.teamId}`)}
              className="card-hover cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="badge badge-purple">{team.teamCode}</span>
              </div>
              <h3 className="font-semibold text-slate-800">{team.name || team.teamCode}</h3>
              <div className="flex flex-wrap gap-2 mt-3">
                {team.members.map(m => (
                  <span key={m.studentId} className="flex items-center gap-1 text-xs text-slate-600 bg-slate-50 border border-slate-100 rounded-full px-2.5 py-1">
                    {m.role === 'lead' && <Crown size={10} className="text-gold-500" />}
                    {m.name}
                  </span>
                ))}
              </div>
              <div className="flex justify-end mt-3">
                <span className="flex items-center gap-1 text-teal-600 text-sm font-medium">
                  Open Team <ChevronRight size={15} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeamProgress;
