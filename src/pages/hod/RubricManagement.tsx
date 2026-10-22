import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRubrics, approveRubric } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { CheckCircle, Scale, Clock } from 'lucide-react';

const RubricManagement: React.FC = () => {
  const qc = useQueryClient();
  const { data: rubrics, isLoading, isError, refetch } = useQuery({
    queryKey: ['rubrics'],
    queryFn: getRubrics,
  });

  const approveMutation = useMutation({
    mutationFn: (rubricId: string) => approveRubric(rubricId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rubrics'] }),
  });

  if (isLoading) return <LoadingState message="Loading rubrics..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Rubric Management</h1>
        <p className="text-slate-500 mt-1">Review and approve faculty-created rubrics for your department</p>
      </div>

      {!rubrics?.length ? (
        <EmptyState icon={<Scale size={28} />} title="No rubrics yet" description="Faculty can create rubrics from the Rubric Builder. They'll appear here for your approval." />
      ) : (
        <div className="space-y-5">
          {rubrics.map(r => (
            <div key={r.rubricId} className="card">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-navy-900">
                    {r.name} <span className="text-xs font-normal text-slate-400">v{r.version}</span>
                  </h3>
                  <p className="text-sm text-slate-500 mt-1">
                    Department: {r.department} · Created by {r.createdBy}
                    {r.academicYear && ` · ${r.academicYear}`}
                  </p>
                </div>
                <div>
                  {r.isApproved ? (
                    <span className="badge badge-teal"><CheckCircle size={11} /> Approved</span>
                  ) : (
                    <span className="badge badge-orange"><Clock size={11} /> Pending</span>
                  )}
                </div>
              </div>

              <div className="space-y-2 mb-4">
                {r.criteria.map(c => (
                  <div key={c.criteriaId} className="flex items-center gap-3 bg-slate-50 rounded-xl px-4 py-2.5 border border-slate-100">
                    <div className="flex-1">
                      <span className="font-medium text-slate-700 text-sm">{c.name}</span>
                      {c.description && <span className="text-xs text-slate-400 ml-2">{c.description}</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-teal-700 text-sm">{c.weight}%</span>
                      {c.isRequired && <span className="badge badge-navy text-[9px]">Required</span>}
                    </div>
                  </div>
                ))}
              </div>

              {!r.isApproved && (
                <button
                  onClick={() => approveMutation.mutate(r.rubricId)}
                  disabled={approveMutation.isPending}
                  className="btn-primary"
                >
                  <CheckCircle size={15} /> Approve Rubric
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RubricManagement;
