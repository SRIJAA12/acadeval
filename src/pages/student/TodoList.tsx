import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyTasks, createTask, updateTaskStatus, getMyProjects } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import {
  ListChecks, Plus, CheckCircle, Circle, Loader2, GraduationCap, CalendarClock, Users, User as UserIcon,
} from 'lucide-react';
import type { TaskItem, TaskSource } from '../../types';
import clsx from 'clsx';

const SOURCE_LABEL: Record<TaskSource, { label: string; icon: React.ReactNode; className: string }> = {
  manual: { label: 'Personal', icon: <UserIcon size={11} />, className: 'badge-slate' },
  guide_request: { label: 'From Guide', icon: <GraduationCap size={11} />, className: 'badge-gold' },
  review_scheduled: { label: 'Review Scheduled', icon: <CalendarClock size={11} />, className: 'badge-navy' },
  team: { label: 'Team', icon: <Users size={11} />, className: 'badge-purple' },
};

const TaskRow: React.FC<{ task: TaskItem; onToggle: () => void; isToggling: boolean }> = ({ task, onToggle, isToggling }) => {
  const src = SOURCE_LABEL[task.source];
  return (
    <div className="flex items-start gap-3 bg-slate-50 rounded-xl p-3 border border-slate-100">
      <button onClick={onToggle} disabled={isToggling} className="mt-0.5 flex-shrink-0">
        {isToggling ? <Loader2 size={18} className="animate-spin text-slate-400" /> :
          task.status === 'done' ? <CheckCircle size={18} className="text-teal-500" /> : <Circle size={18} className="text-slate-300" />}
      </button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className={clsx('text-sm font-medium', task.status === 'done' ? 'text-slate-400 line-through' : 'text-slate-700')}>{task.title}</p>
          <span className={clsx('badge text-[9px]', src.className)}>{src.icon}{src.label}</span>
        </div>
        {task.description && <p className="text-xs text-slate-500 mt-1">{task.description}</p>}
        <p className="text-xs text-slate-400 mt-1">
          {task.projectTitle && `${task.projectTitle}`}
          {task.teamCode && `Team ${task.teamCode}`}
          {task.dueDate && ` · Due ${new Date(task.dueDate).toLocaleDateString()}`}
          {task.createdByName && ` · From ${task.createdByName}`}
        </p>
      </div>
    </div>
  );
};

const TodoList: React.FC = () => {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [projectId, setProjectId] = useState('');
  const [dueDate, setDueDate] = useState('');

  const { data: tasks, isLoading, isError, refetch } = useQuery({
    queryKey: ['myTasks'],
    queryFn: getMyTasks,
  });

  const { data: projects } = useQuery({ queryKey: ['myProjects'], queryFn: getMyProjects });

  const createMutation = useMutation({
    mutationFn: () => createTask({ title, projectId: projectId || undefined, dueDate: dueDate || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['myTasks'] });
      setShowForm(false); setTitle(''); setProjectId(''); setDueDate('');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'pending' | 'done' }) => updateTaskStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['myTasks'] }),
  });
  const [togglingId, setTogglingId] = useState<string | null>(null);

  if (isLoading) return <LoadingState message="Loading your to-dos..." />;
  if (isError) return <ErrorState retry={refetch} />;

  const pending = (tasks || []).filter(t => t.status === 'pending');
  const done = (tasks || []).filter(t => t.status === 'done');

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900">To-Do</h1>
          <p className="text-slate-500 mt-1">Personal tasks, guide requests, scheduled reviews, and team assignments — all in one place.</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="btn-primary flex-shrink-0"><Plus size={16} /> Add Task</button>
      </div>

      {showForm && (
        <div className="card mb-6 space-y-3 animate-fade-in">
          <input value={title} onChange={e => setTitle(e.target.value)} className="input" placeholder="Task title" />
          <div className="grid grid-cols-2 gap-3">
            <select value={projectId} onChange={e => setProjectId(e.target.value)} className="input">
              <option value="">No project</option>
              {(projects || []).map(p => <option key={p.projectId} value={p.projectId}>{p.title}</option>)}
            </select>
            <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} className="input" />
          </div>
          <div className="flex gap-2">
            <button onClick={() => createMutation.mutate()} disabled={!title.trim() || createMutation.isPending} className="btn-primary">
              {createMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Add
            </button>
            <button onClick={() => setShowForm(false)} className="btn-outline">Cancel</button>
          </div>
        </div>
      )}

      {!tasks?.length ? (
        <EmptyState icon={<ListChecks size={28} />} title="Nothing on your to-do yet" description="Tasks from your guide, scheduled reviews, your teams, and anything you add yourself will show up here." />
      ) : (
        <div className="space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Pending ({pending.length})</h2>
            {pending.length === 0 ? (
              <p className="text-sm text-slate-400">Nothing pending — you're all caught up.</p>
            ) : (
              <div className="space-y-2">
                {pending.map(t => (
                  <TaskRow
                    key={t.taskId}
                    task={t}
                    isToggling={togglingId === t.taskId && toggleMutation.isPending}
                    onToggle={() => { setTogglingId(t.taskId); toggleMutation.mutate({ id: t.taskId, status: 'done' }, { onSettled: () => setTogglingId(null) }); }}
                  />
                ))}
              </div>
            )}
          </div>

          {done.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Completed ({done.length})</h2>
              <div className="space-y-2">
                {done.map(t => (
                  <TaskRow
                    key={t.taskId}
                    task={t}
                    isToggling={togglingId === t.taskId && toggleMutation.isPending}
                    onToggle={() => { setTogglingId(t.taskId); toggleMutation.mutate({ id: t.taskId, status: 'pending' }, { onSettled: () => setTogglingId(null) }); }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TodoList;
