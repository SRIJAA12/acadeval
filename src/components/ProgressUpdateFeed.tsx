import React, { useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProgressUpdates, postProgressUpdate, downloadProgressAttachment } from '../api/endpoints';
import { TrendingUp, Send, Paperclip, GitBranch, Download, X } from 'lucide-react';

interface Props {
  projectId: string;
  /** Student owner can post; guide/reviewer/HOD get a read-only feed. */
  canPost: boolean;
}

const ProgressUpdateFeed: React.FC<Props> = ({ projectId, canPost }) => {
  const qc = useQueryClient();
  const [draft, setDraft] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: updates, isLoading } = useQuery({
    queryKey: ['progress', projectId],
    queryFn: () => getProgressUpdates(projectId),
    enabled: !!projectId,
    refetchInterval: 20000,
  });

  const postMutation = useMutation({
    mutationFn: (content: string) => postProgressUpdate(projectId, content, {
      file: file || undefined, githubUrl: githubUrl.trim() || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['progress', projectId] });
      setDraft(''); setGithubUrl(''); setFile(null);
    },
  });

  return (
    <div className="card">
      <h2 className="text-base font-semibold text-navy-900 mb-1 flex items-center gap-2">
        <TrendingUp size={18} className="text-teal-500" /> Progress Updates
      </h2>
      <p className="text-xs text-slate-400 mb-4">
        {canPost
          ? 'Nothing you post here is ever deleted — each update adds to the history below, newest first.'
          : "The student's latest update is shown first; older entries stay below it."}
      </p>

      {canPost && (
        <div className="mb-5 space-y-2">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={3}
            className="input resize-none text-sm"
            placeholder="What did you work on? Share progress, blockers, or questions..."
          />
          <div className="relative">
            <GitBranch size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={githubUrl}
              onChange={e => setGithubUrl(e.target.value)}
              className="input pl-9 text-sm"
              placeholder="Optional: GitHub link to your updated code"
            />
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={e => setFile(e.target.files?.[0] || null)}
          />
          <div className="flex items-center gap-2">
            <button onClick={() => fileInputRef.current?.click()} className="btn-outline text-xs py-1.5">
              <Paperclip size={12} /> {file ? 'Change File' : 'Attach Doc / PPT (optional)'}
            </button>
            {file && (
              <span className="flex items-center gap-1 text-xs text-slate-500 bg-slate-50 px-2 py-1 rounded-lg border border-slate-100">
                {file.name}
                <button onClick={() => setFile(null)}><X size={11} className="text-slate-400 hover:text-red-500" /></button>
              </span>
            )}
          </div>
          <button
            onClick={() => draft.trim() && postMutation.mutate(draft.trim())}
            disabled={!draft.trim() || postMutation.isPending}
            className="btn-primary text-sm mt-2"
          >
            <Send size={14} /> Post Update
          </button>
        </div>
      )}

      {isLoading && <div className="animate-pulse h-16 bg-slate-50 rounded-xl" />}
      {!isLoading && (!updates || updates.length === 0) && (
        <p className="text-sm text-slate-400 text-center py-6">
          {canPost ? 'No progress posted yet — share your first update above.' : 'The student has not posted any progress yet.'}
        </p>
      )}

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {updates?.map((u, i) => (
          <div
            key={u.updateId}
            className={`rounded-xl p-3 border ${i === 0 ? 'bg-teal-50 border-teal-200' : 'bg-slate-50 border-slate-100'}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-600">
                {u.authorName}{i === 0 && <span className="ml-2 badge badge-teal text-[9px]">Latest</span>}
              </span>
              <span className="text-[10px] text-slate-400">{new Date(u.createdAt).toLocaleString()}</span>
            </div>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{u.content}</p>
            {(u.attachmentFilename || u.githubUrl) && (
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {u.attachmentFilename && (
                  <button
                    onClick={() => downloadProgressAttachment(projectId, u.updateId, u.attachmentFilename!)}
                    className="flex items-center gap-1 text-xs text-teal-700 bg-teal-50 border border-teal-200 px-2 py-1 rounded-lg hover:bg-teal-100"
                  >
                    <Download size={11} /> {u.attachmentFilename}
                  </button>
                )}
                {u.githubUrl && (
                  <a
                    href={u.githubUrl} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-navy-700 bg-navy-50 border border-navy-100 px-2 py-1 rounded-lg hover:bg-navy-100"
                  >
                    <GitBranch size={11} /> View on GitHub
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProgressUpdateFeed;
