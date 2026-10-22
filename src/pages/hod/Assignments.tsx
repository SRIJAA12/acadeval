import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUnassignedProjects, assignProject, getUsers } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { UserCog, CheckCircle2 } from 'lucide-react';
import Badge from '../../components/Badge';

const Assignments: React.FC = () => {
  const qc = useQueryClient();
  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['unassignedProjects'],
    queryFn: getUnassignedProjects,
  });
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers });

  const guides = (users || []).filter(u => u.role === 'guide');
  const reviewers = (users || []).filter(u => u.role === 'reviewer');

  const [selections, setSelections] = useState<Record<string, { guideId?: string; reviewerId?: string }>>({});

  const assignMutation = useMutation({
    mutationFn: ({ projectId, guideId, reviewerId }: { projectId: string; guideId?: string; reviewerId?: string }) =>
      assignProject(projectId, { guideId, reviewerId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unassignedProjects'] }),
  });

  if (isLoading) return <LoadingState message="Loading unassigned projects..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Guide & Reviewer Assignment</h1>
        <p className="text-slate-500 mt-1">
          A project is invisible to faculty until assigned — only the assigned guide/reviewer (or HOD) can score, review, or publish it.
        </p>
      </div>

      {!projects?.length ? (
        <EmptyState
          icon={<UserCog size={28} />}
          title="All projects are assigned"
          description="Every submitted project currently has both a guide and a reviewer."
        />
      ) : (
        <div className="space-y-4">
          {projects.map(p => {
            const sel = selections[p.projectId] || {};
            return (
              <div key={p.projectId} className="card">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <Badge type="domain" value={p.domain} size="sm" />
                      <Badge type="pipeline" value={p.pipelineStatus} size="sm" />
                    </div>
                    <h3 className="font-semibold text-slate-800">{p.title}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">by {p.studentName} ({p.rollNo})</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                  <div>
                    <label className="label">Guide {p.guideName && <span className="text-teal-600">— currently {p.guideName}</span>}</label>
                    <select
                      className="input text-sm"
                      value={sel.guideId ?? ''}
                      onChange={e => setSelections(prev => ({ ...prev, [p.projectId]: { ...prev[p.projectId], guideId: e.target.value || undefined } }))}
                    >
                      <option value="">{p.guideName ? 'Keep current' : 'Select guide...'}</option>
                      {guides.map(g => <option key={g.userId} value={g.userId}>{g.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Reviewer {p.reviewerName && <span className="text-teal-600">— currently {p.reviewerName}</span>}</label>
                    <select
                      className="input text-sm"
                      value={sel.reviewerId ?? ''}
                      onChange={e => setSelections(prev => ({ ...prev, [p.projectId]: { ...prev[p.projectId], reviewerId: e.target.value || undefined } }))}
                    >
                      <option value="">{p.reviewerName ? 'Keep current' : 'Select reviewer...'}</option>
                      {reviewers.map(r => <option key={r.userId} value={r.userId}>{r.name}</option>)}
                    </select>
                  </div>
                  <button
                    onClick={() => assignMutation.mutate({ projectId: p.projectId, guideId: sel.guideId, reviewerId: sel.reviewerId })}
                    disabled={(!sel.guideId && !sel.reviewerId) || assignMutation.isPending}
                    className="btn-primary text-sm"
                  >
                    <CheckCircle2 size={15} /> Assign
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Assignments;
