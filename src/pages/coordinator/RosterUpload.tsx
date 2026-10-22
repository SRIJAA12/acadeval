import React, { useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRoster, uploadRoster, getAllTeams } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import { UploadCloud, FileSpreadsheet, CheckCircle, Clock, AlertCircle, Info, Users, Crown } from 'lucide-react';
import clsx from 'clsx';

const RosterUpload: React.FC = () => {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const { data: roster, isLoading, isError, refetch } = useQuery({
    queryKey: ['roster'],
    queryFn: getRoster,
  });

  const { data: teams, isLoading: teamsLoading } = useQuery({
    queryKey: ['allTeams'],
    queryFn: getAllTeams,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadRoster(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roster'] }),
  });

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    setFileName(file.name);
    uploadMutation.mutate(file);
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Roster &amp; Allocation</h1>
        <p className="text-slate-500 mt-1">Upload an Excel roster to auto-assign guides to students and teams — individually or in bulk.</p>
      </div>

      <div className="card mb-6">
        <div className="flex items-start gap-3 bg-indigo-50 border border-indigo-100 rounded-xl p-4 mb-5">
          <Info size={16} className="text-indigo-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-indigo-800 space-y-1">
            <p className="font-semibold">Expected .xlsx columns (header row, any order):</p>
            <p><code className="bg-white/60 px-1.5 py-0.5 rounded">Roll No</code> (required) · <code className="bg-white/60 px-1.5 py-0.5 rounded">Guide Email</code> (required) · <code className="bg-white/60 px-1.5 py-0.5 rounded">Student Email</code> · <code className="bg-white/60 px-1.5 py-0.5 rounded">Team ID</code> · <code className="bg-white/60 px-1.5 py-0.5 rounded">Domain</code> (all optional)</p>
            <p>Rows for students who already submitted are applied immediately; others are applied automatically the moment that student submits. Give two or more rows the same Team ID to allocate them together as a team for review-round scheduling.</p>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xlsm"
          className="hidden"
          onChange={e => handleFile(e.target.files?.[0])}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="w-full border-2 border-dashed border-slate-200 hover:border-indigo-300 rounded-2xl py-10 flex flex-col items-center gap-2 transition-colors"
        >
          <UploadCloud size={28} className="text-indigo-400" />
          <span className="text-sm font-medium text-slate-600">
            {uploadMutation.isPending ? 'Uploading...' : fileName || 'Click to choose an .xlsx roster file'}
          </span>
        </button>

        {uploadMutation.isError && (
          <div className="mt-4 flex items-center gap-2 text-red-600 text-sm bg-red-50 px-4 py-3 rounded-xl border border-red-100">
            <AlertCircle size={16} /> Upload failed. Check the file format and try again.
          </div>
        )}

        {uploadMutation.data && (
          <div className="mt-5 space-y-3">
            <div className="flex gap-3">
              <span className="badge badge-teal">{uploadMutation.data.applied} applied</span>
              <span className="badge badge-gold">{uploadMutation.data.pending} pending</span>
              {uploadMutation.data.errors > 0 && <span className="badge badge-red">{uploadMutation.data.errors} errors</span>}
            </div>
            <div className="space-y-1.5 max-h-56 overflow-y-auto">
              {uploadMutation.data.results.map(r => (
                <div key={r.rowNumber} className="flex items-center gap-2 text-xs bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
                  {r.status === 'applied' && <CheckCircle size={13} className="text-teal-500 flex-shrink-0" />}
                  {r.status === 'pending' && <Clock size={13} className="text-gold-500 flex-shrink-0" />}
                  {r.status === 'error' && <AlertCircle size={13} className="text-red-500 flex-shrink-0" />}
                  <span className="font-medium text-slate-600">Row {r.rowNumber}{r.rollNo && ` (${r.rollNo})`}:</span>
                  <span className="text-slate-500">{r.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="font-semibold text-navy-900 mb-4">Allocation History</h2>
        {isLoading && <LoadingState message="Loading roster..." />}
        {isError && <ErrorState retry={refetch} />}
        {!isLoading && !isError && (!roster || roster.length === 0) && (
          <EmptyState icon={<FileSpreadsheet size={28} />} title="No roster uploaded yet" description="Upload an Excel file above to begin allocating guides." />
        )}
        {!isLoading && roster && roster.length > 0 && (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Roll No</th>
                  <th>Student Email</th>
                  <th>Team</th>
                  <th>Guide</th>
                  <th>Domain</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {roster.map(r => (
                  <tr key={r.allocationId}>
                    <td className="font-medium text-slate-700">{r.rollNo}</td>
                    <td className="text-sm text-slate-500">{r.studentEmail || '—'}</td>
                    <td className="text-sm text-slate-500">{r.teamId || '—'}</td>
                    <td className="text-sm text-slate-500">{r.guideName || '—'}</td>
                    <td className="text-sm text-slate-500">{r.domain || '—'}</td>
                    <td>
                      {r.error ? (
                        <span className="badge badge-red" title={r.error}>Error</span>
                      ) : (
                        <span className={clsx('badge', r.isApplied ? 'badge-teal' : 'badge-gold')}>
                          {r.isApplied ? 'Applied' : 'Pending Submission'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card mt-6">
        <h2 className="font-semibold text-navy-900 mb-1 flex items-center gap-2"><Users size={16} className="text-purple-500" /> Teams</h2>
        <p className="text-xs text-slate-400 mb-4">Created automatically from the roster's Team ID column — every row sharing a Team ID becomes one team.</p>
        {teamsLoading && <p className="text-sm text-slate-400">Loading...</p>}
        {!teamsLoading && (!teams || teams.length === 0) && (
          <p className="text-sm text-slate-400">No teams yet — upload a roster with a Team ID column to create some.</p>
        )}
        {!teamsLoading && teams && teams.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {teams.map(t => (
              <div key={t.teamId} className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <span className="badge badge-purple mb-2">{t.teamCode}</span>
                <div className="flex flex-wrap gap-1.5">
                  {t.members.map(m => (
                    <span key={m.studentId} className="flex items-center gap-1 text-xs text-slate-600 bg-white border border-slate-100 rounded-full px-2 py-0.5">
                      {m.role === 'lead' && <Crown size={10} className="text-gold-500" />}
                      {m.name}
                    </span>
                  ))}
                  {t.members.length === 0 && <span className="text-xs text-slate-400">No members yet</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RosterUpload;
