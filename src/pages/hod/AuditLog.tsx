import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLogs } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { ScrollText, UserCog, Scale, Send, Shield } from 'lucide-react';

const ACTION_META: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
  assign_project: { label: 'Assigned project', icon: <UserCog size={14} />, className: 'text-teal-700 bg-teal-50' },
  publish_review: { label: 'Published review', icon: <Send size={14} />, className: 'text-navy-700 bg-navy-50' },
  approve_rubric: { label: 'Approved rubric', icon: <Scale size={14} />, className: 'text-gold-700 bg-gold-50' },
  change_role: { label: 'Changed user role', icon: <Shield size={14} />, className: 'text-red-700 bg-red-50' },
};

const AuditLog: React.FC = () => {
  const { data: logs, isLoading, isError, refetch } = useQuery({
    queryKey: ['auditLogs'],
    queryFn: () => getAuditLogs(200),
    refetchInterval: 30000,
  });

  if (isLoading) return <LoadingState message="Loading audit log..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Audit Log</h1>
        <p className="text-slate-500 mt-1">Who changed what, across assignments, rubric approvals, publishes, and role changes.</p>
      </div>

      {!logs?.length ? (
        <EmptyState icon={<ScrollText size={28} />} title="No audit entries yet" description="Actions like assignment, rubric approval, and role changes will appear here." />
      ) : (
        <div className="card divide-y divide-slate-100">
          {logs.map(entry => {
            const meta = ACTION_META[entry.action] || { label: entry.action, icon: <ScrollText size={14} />, className: 'text-slate-700 bg-slate-50' };
            return (
              <div key={entry.auditLogId} className="py-3 flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${meta.className}`}>
                  {meta.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-800">
                    <span className="font-semibold">{entry.actorName}</span>{' '}
                    <span className="text-slate-500">({entry.actorRole})</span>{' '}
                    {meta.label.toLowerCase()}
                    <span className="text-slate-400"> — {entry.entityType} {entry.entityId.slice(0, 8)}</span>
                  </p>
                  {Object.keys(entry.details || {}).length > 0 && (
                    <p className="text-xs text-slate-400 mt-0.5 font-mono truncate">
                      {JSON.stringify(entry.details)}
                    </p>
                  )}
                </div>
                <span className="text-xs text-slate-400 flex-shrink-0">{new Date(entry.createdAt).toLocaleString('en-IN')}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AuditLog;
