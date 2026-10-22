import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/AuthContext';
import {
  getTeam, getTeamMessages, postTeamMessage, getTeamTasks, createTeamTask, updateTaskStatus,
} from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import {
  ArrowLeft, Users, Crown, Send, AtSign, ListChecks, Plus, CheckCircle, Circle, Loader2,
} from 'lucide-react';
import clsx from 'clsx';

const TeamDiscussion: React.FC<{ teamId: string; memberNames: string[] }> = ({ teamId, memberNames }) => {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [draft, setDraft] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  const { data: messages, isLoading } = useQuery({
    queryKey: ['teamMessages', teamId],
    queryFn: () => getTeamMessages(teamId),
    refetchInterval: 15000,
  });

  const postMutation = useMutation({
    mutationFn: (body: string) => postTeamMessage(teamId, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['teamMessages', teamId] }); setDraft(''); },
  });

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages?.length]);

  const insertMention = (name: string) => setDraft(prev => `${prev}${prev.endsWith(' ') || prev === '' ? '' : ' '}@${name} `);

  return (
    <div className="card">
      <h2 className="text-base font-semibold text-navy-900 mb-1 flex items-center gap-2">
        <Users size={18} className="text-teal-500" /> Team Discussion
      </h2>
      <p className="text-xs text-slate-400 mb-4">Open to every team member. Mention someone to notify them directly.</p>

      {isLoading && <div className="animate-pulse h-16 bg-slate-50 rounded-xl" />}
      <div className="space-y-3 max-h-80 overflow-y-auto mb-4">
        {!isLoading && (!messages || messages.length === 0) && (
          <p className="text-sm text-slate-400 text-center py-6">No messages yet. Start the conversation.</p>
        )}
        {messages?.map(m => {
          const mine = m.authorId === user?.id;
          return (
            <div key={m.messageId} className={clsx('flex', mine ? 'justify-end' : 'justify-start')}>
              <div className={clsx('max-w-[75%] rounded-xl px-3 py-2', mine ? 'bg-teal-500 text-white' : 'bg-slate-50 border border-slate-100')}>
                {!mine && <p className="text-[11px] font-semibold text-slate-500 mb-0.5">{m.authorName}</p>}
                <p className="text-sm whitespace-pre-wrap">{m.body}</p>
                <p className={clsx('text-[10px] mt-1', mine ? 'text-teal-100' : 'text-slate-400')}>
                  {new Date(m.createdAt).toLocaleString()}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2">
        {memberNames.map(name => (
          <button key={name} onClick={() => insertMention(name)} className="flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 border border-slate-100 rounded-full px-2 py-0.5 hover:bg-slate-100">
            <AtSign size={10} /> {name}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <textarea
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); draft.trim() && postMutation.mutate(draft.trim()); } }}
          rows={2}
          className="input resize-none text-sm flex-1"
          placeholder="Message the team... use @Name to mention someone"
        />
        <button
          onClick={() => draft.trim() && postMutation.mutate(draft.trim())}
          disabled={!draft.trim() || postMutation.isPending}
          className="btn-primary self-end"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
};

const TeamTasks: React.FC<{ teamId: string; members: { studentId: string; name: string }[] }> = ({ teamId, members }) => {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [dueDate, setDueDate] = useState('');

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['teamTasks', teamId],
    queryFn: () => getTeamTasks(teamId),
  });

  const createMutation = useMutation({
    mutationFn: () => createTeamTask(teamId, { title, assigneeId: assigneeId || undefined, dueDate: dueDate || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teamTasks', teamId] });
      setShowForm(false); setTitle(''); setAssigneeId(''); setDueDate('');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'pending' | 'done' }) => updateTaskStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['teamTasks', teamId] }),
  });

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-base font-semibold text-navy-900 flex items-center gap-2">
          <ListChecks size={18} className="text-indigo-500" /> Team Tasks
        </h2>
        <button onClick={() => setShowForm(v => !v)} className="btn-outline text-xs py-1.5"><Plus size={13} /> Assign Task</button>
      </div>
      <p className="text-xs text-slate-400 mb-4">Any member can assign a task to any other member.</p>

      {showForm && (
        <div className="bg-slate-50 rounded-xl p-3 border border-slate-100 mb-4 space-y-2">
          <input value={title} onChange={e => setTitle(e.target.value)} className="input text-sm" placeholder="Task title" />
          <div className="grid grid-cols-2 gap-2">
            <select value={assigneeId} onChange={e => setAssigneeId(e.target.value)} className="input text-sm">
              <option value="">Assign to myself</option>
              {members.filter(m => m.studentId !== user?.id).map(m => (
                <option key={m.studentId} value={m.studentId}>{m.name}</option>
              ))}
            </select>
            <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} className="input text-sm" />
          </div>
          <button onClick={() => createMutation.mutate()} disabled={!title.trim() || createMutation.isPending} className="btn-primary text-sm">
            {createMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} Create Task
          </button>
        </div>
      )}

      {isLoading && <div className="animate-pulse h-16 bg-slate-50 rounded-xl" />}
      {!isLoading && (!tasks || tasks.length === 0) && <p className="text-sm text-slate-400 text-center py-4">No tasks yet.</p>}
      <div className="space-y-2">
        {tasks?.map(t => (
          <div key={t.taskId} className="flex items-start gap-3 bg-slate-50 rounded-xl p-3 border border-slate-100">
            <button
              onClick={() => toggleMutation.mutate({ id: t.taskId, status: t.status === 'done' ? 'pending' : 'done' })}
              className="mt-0.5 flex-shrink-0"
            >
              {t.status === 'done' ? <CheckCircle size={18} className="text-teal-500" /> : <Circle size={18} className="text-slate-300" />}
            </button>
            <div className="flex-1 min-w-0">
              <p className={clsx('text-sm font-medium', t.status === 'done' ? 'text-slate-400 line-through' : 'text-slate-700')}>{t.title}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                Assigned to {t.assigneeName}{t.createdByName && t.createdByName !== t.assigneeName ? ` by ${t.createdByName}` : ''}
                {t.dueDate && ` · Due ${new Date(t.dueDate).toLocaleDateString()}`}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const TeamProgressDetail: React.FC = () => {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();

  const { data: team, isLoading, isError, refetch } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => getTeam(teamId!),
    enabled: !!teamId,
  });

  if (isLoading) return <LoadingState message="Loading team..." />;
  if (isError || !team) return <ErrorState retry={refetch} />;

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <button onClick={() => navigate('/student/team-progress')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={15} /> All Teams
      </button>

      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <span className="badge badge-purple">{team.teamCode}</span>
        </div>
        <h1 className="text-xl font-display font-bold text-navy-900">{team.name || team.teamCode}</h1>
        <div className="flex flex-wrap gap-2 mt-3">
          {team.members.map(m => (
            <span key={m.studentId} className="flex items-center gap-1 text-xs text-slate-600 bg-slate-50 border border-slate-100 rounded-full px-2.5 py-1">
              {m.role === 'lead' && <Crown size={10} className="text-gold-500" />}
              {m.name}{m.rollNo ? ` · ${m.rollNo}` : ''}
            </span>
          ))}
        </div>
      </div>

      <TeamDiscussion teamId={team.teamId} memberNames={team.members.map(m => m.name)} />
      <TeamTasks teamId={team.teamId} members={team.members} />
    </div>
  );
};

export default TeamProgressDetail;
