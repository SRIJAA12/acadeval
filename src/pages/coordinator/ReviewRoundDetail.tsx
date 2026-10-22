import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getReviewRounds, getRoundAssignments, createRoundAssignment, getReviewerSlots, getAllProjects,
} from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { ArrowLeft, Users, Plus, Mail, CheckCircle, Clock } from 'lucide-react';

const ReviewRoundDetail: React.FC = () => {
  const { roundId } = useParams<{ roundId: string }>();
  const qc = useQueryClient();

  const [mode, setMode] = useState<'projects' | 'team'>('projects');
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);
  const [teamId, setTeamId] = useState('');
  const [reviewerSlotId, setReviewerSlotId] = useState('');
  const [staffEmail, setStaffEmail] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');

  const { data: rounds } = useQuery({ queryKey: ['reviewRounds'], queryFn: getReviewRounds });
  const round = rounds?.find(r => r.roundId === roundId);

  const { data: assignments, isLoading, isError, refetch } = useQuery({
    queryKey: ['roundAssignments', roundId],
    queryFn: () => getRoundAssignments(roundId!),
    enabled: !!roundId,
  });

  const { data: slots } = useQuery({ queryKey: ['reviewerSlots'], queryFn: getReviewerSlots });
  const { data: projects } = useQuery({ queryKey: ['allProjects'], queryFn: getAllProjects });

  const assignMutation = useMutation({
    mutationFn: () => createRoundAssignment(roundId!, {
      projectIds: mode === 'projects' ? selectedProjectIds : undefined,
      teamId: mode === 'team' ? teamId : undefined,
      reviewerSlotId, staffEmail, scheduledAt: scheduledAt || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roundAssignments', roundId] });
      qc.invalidateQueries({ queryKey: ['reviewRounds'] });
      setSelectedProjectIds([]); setTeamId(''); setReviewerSlotId(''); setStaffEmail(''); setScheduledAt('');
    },
  });

  const toggleProject = (id: string) => {
    setSelectedProjectIds(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]);
  };

  const canSubmit = reviewerSlotId && staffEmail.trim() && (mode === 'projects' ? selectedProjectIds.length > 0 : teamId.trim());

  return (
    <div className="max-w-5xl mx-auto">
      <Link to="/coordinator/review-rounds" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4">
        <ArrowLeft size={14} /> Back to Review Rounds
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-display font-bold text-navy-900">{round?.name || 'Review Round'}</h1>
        {round?.description && <p className="text-slate-500 mt-1">{round.description}</p>}
      </div>

      <div className="card mb-6 space-y-4">
        <h2 className="font-semibold text-navy-900 flex items-center gap-2"><Plus size={16} /> Schedule a Reviewer Assignment</h2>

        <div className="flex gap-2">
          <button onClick={() => setMode('projects')} className={`btn-outline text-sm ${mode === 'projects' ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : ''}`}>By Project</button>
          <button onClick={() => setMode('team')} className={`btn-outline text-sm ${mode === 'team' ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : ''}`}>By Team ID</button>
        </div>

        {mode === 'projects' ? (
          <div>
            <label className="label">Select Projects</label>
            <div className="max-h-48 overflow-y-auto border border-slate-100 rounded-xl divide-y divide-slate-100">
              {(projects || []).map(p => (
                <label key={p.projectId} className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedProjectIds.includes(p.projectId)}
                    onChange={() => toggleProject(p.projectId)}
                    className="w-4 h-4 accent-indigo-500"
                  />
                  <span className="flex-1 text-slate-700">{p.title}</span>
                  {p.reviewerReadyAt && <span className="badge badge-teal text-[9px]">Ready for Review</span>}
                  <span className="text-xs text-slate-400">{p.studentName}{p.teamId ? ` · Team ${p.teamId}` : ''}</span>
                </label>
              ))}
              {(!projects || projects.length === 0) && <p className="text-sm text-slate-400 px-3 py-4">No projects found.</p>}
            </div>
          </div>
        ) : (
          <div>
            <label className="label">Team ID</label>
            <input value={teamId} onChange={e => setTeamId(e.target.value)} className="input" placeholder="e.g. TEAM-A (every project with this team tag is assigned together)" />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Reviewer Slot</label>
            <select value={reviewerSlotId} onChange={e => setReviewerSlotId(e.target.value)} className="input">
              <option value="">Select a slot...</option>
              {(slots || []).map(s => <option key={s.slotId} value={s.slotId}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Scheduled At</label>
            <input type="datetime-local" value={scheduledAt} onChange={e => setScheduledAt(e.target.value)} className="input" />
          </div>
        </div>

        <div>
          <label className="label">Real Staff Email (credentials are sent here)</label>
          <input type="email" value={staffEmail} onChange={e => setStaffEmail(e.target.value)} className="input" placeholder="staff.member@college.edu" />
        </div>

        <button onClick={() => assignMutation.mutate()} disabled={!canSubmit || assignMutation.isPending} className="btn-primary">
          <Mail size={15} /> Assign &amp; Email Credentials
        </button>
        {assignMutation.isError && (
          <p className="text-sm text-red-600">Could not create the assignment. Check the selections above.</p>
        )}
      </div>

      <div className="card">
        <h2 className="font-semibold text-navy-900 mb-4 flex items-center gap-2"><Users size={16} /> Scheduled Assignments</h2>
        {isLoading && <LoadingState message="Loading assignments..." />}
        {isError && <ErrorState retry={refetch} />}
        {!isLoading && !isError && (!assignments || assignments.length === 0) && (
          <EmptyState icon={<Users size={28} />} title="No assignments yet" description="Use the form above to schedule a reviewer for this round." />
        )}
        {!isLoading && assignments && assignments.length > 0 && (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Student</th>
                  <th>Reviewer Slot</th>
                  <th>Staff Email</th>
                  <th>Scheduled</th>
                  <th>Credentials</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map(a => (
                  <tr key={a.assignmentId}>
                    <td className="font-medium text-slate-700">{a.projectTitle}</td>
                    <td className="text-sm text-slate-500">{a.studentName}</td>
                    <td className="text-sm text-slate-500">{a.reviewerSlotName}</td>
                    <td className="text-sm text-slate-500">{a.staffEmail}</td>
                    <td className="text-sm text-slate-500">{a.scheduledAt ? new Date(a.scheduledAt).toLocaleString('en-IN') : '—'}</td>
                    <td>
                      {a.credentialEmailSent ? (
                        <span className="badge badge-teal"><CheckCircle size={11} /> Sent</span>
                      ) : (
                        <span className="badge badge-gold"><Clock size={11} /> Not Sent</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewRoundDetail;
