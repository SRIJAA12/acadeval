import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDiscussion, postDiscussionMessage, markDiscussionRead } from '../api/endpoints';
import { useAuth } from '../auth/AuthContext';
import { MessageSquare, Send } from 'lucide-react';
import clsx from 'clsx';

interface Props {
  projectId: string;
}

const DiscussionThread: React.FC<Props> = ({ projectId }) => {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [draft, setDraft] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  const { data: messages, isLoading } = useQuery({
    queryKey: ['discussion', projectId],
    queryFn: () => getDiscussion(projectId),
    enabled: !!projectId,
    refetchInterval: 15000,
  });

  const postMutation = useMutation({
    mutationFn: (body: string) => postDiscussionMessage(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['discussion', projectId] });
      setDraft('');
    },
  });

  useEffect(() => {
    if (messages?.some(m => m.unread)) {
      markDiscussionRead(projectId).then(() => {
        qc.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      });
    }
  }, [messages, projectId, qc]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [messages?.length]);

  const handleSend = () => {
    if (!draft.trim()) return;
    postMutation.mutate(draft.trim());
  };

  return (
    <div className="card flex flex-col max-h-[420px]">
      <h2 className="text-base font-semibold text-navy-900 mb-4 flex items-center gap-2">
        <MessageSquare size={18} className="text-teal-500" /> Discussion
      </h2>

      <div className="flex-1 overflow-y-auto space-y-3 mb-3 min-h-[120px]">
        {isLoading && <div className="animate-pulse h-20 bg-slate-50 rounded-xl" />}
        {!isLoading && (!messages || messages.length === 0) && (
          <p className="text-sm text-slate-400 text-center py-6">No messages yet. Start the conversation.</p>
        )}
        {messages?.map(m => {
          const isMine = m.authorId === user?.id;
          return (
            <div key={m.messageId} className={clsx('flex', isMine ? 'justify-end' : 'justify-start')}>
              <div className={clsx(
                'max-w-[80%] rounded-2xl px-4 py-2.5 text-sm',
                isMine ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-800'
              )}>
                {!isMine && (
                  <p className="text-[11px] font-semibold text-teal-600 mb-0.5 capitalize">{m.authorName} · {m.authorRole}</p>
                )}
                <p>{m.body}</p>
                <p className={clsx('text-[10px] mt-1', isMine ? 'text-white/60' : 'text-slate-400')}>
                  {new Date(m.createdAt).toLocaleString()}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      <div className="flex gap-2">
        <input
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
          className="input text-sm flex-1"
          placeholder="Write a message..."
        />
        <button onClick={handleSend} disabled={!draft.trim() || postMutation.isPending} className="btn-primary px-4">
          <Send size={15} />
        </button>
      </div>
    </div>
  );
};

export default DiscussionThread;
