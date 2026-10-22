import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAllProjects, createTask } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import GuideFeedbackPanel from '../../components/GuideFeedbackPanel';
import ProgressUpdateFeed from '../../components/ProgressUpdateFeed';
import DiscussionThread from '../../components/DiscussionThread';
import { ArrowLeft, GraduationCap, ListChecks, Plus, Loader2, CheckCircle } from 'lucide-react';

const ProjectDiscussion: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDue, setTaskDue] = useState('');
  const [justAssigned, setJustAssigned] = useState(false);

  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['allProjects'],
    queryFn: getAllProjects,
  });

  const assignTaskMutation = useMutation({
    mutationFn: () => createTask({ title: taskTitle, projectId, dueDate: taskDue || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['myTasks'] });
      setShowTaskForm(false); setTaskTitle(''); setTaskDue('');
      setJustAssigned(true);
      setTimeout(() => setJustAssigned(false), 3000);
    },
  });

  if (isLoading) return <LoadingState message="Loading project..." />;
  if (isError) return <ErrorState retry={refetch} />;

  const project = projects?.find(p => p.projectId === projectId);
  if (!project) return <ErrorState message="Project not found." retry={() => navigate('/faculty/discussion')} />;

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <button onClick={() => navigate('/faculty/discussion')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={15} /> All Discussions
      </button>

      <div className="card">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-display font-bold text-navy-900">{project.title}</h1>
            <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
              <GraduationCap size={14} /> {project.studentName} · {project.rollNo}
            </p>
          </div>
          <button onClick={() => setShowTaskForm(v => !v)} className="btn-outline text-sm flex-shrink-0">
            <ListChecks size={14} /> Assign Task
          </button>
        </div>

        {showTaskForm && (
          <div className="mt-4 bg-slate-50 rounded-xl p-3 border border-slate-100 space-y-2 animate-fade-in">
            <input value={taskTitle} onChange={e => setTaskTitle(e.target.value)} className="input text-sm" placeholder="What should they do? e.g. Add a related-work section" />
            <div className="flex items-center gap-2">
              <input type="date" value={taskDue} onChange={e => setTaskDue(e.target.value)} className="input text-sm w-auto" />
              <button
                onClick={() => assignTaskMutation.mutate()}
                disabled={!taskTitle.trim() || assignTaskMutation.isPending}
                className="btn-primary text-sm"
              >
                {assignTaskMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} Add to Their To-Do
              </button>
            </div>
          </div>
        )}
        {justAssigned && (
          <p className="mt-3 text-xs text-teal-700 flex items-center gap-1"><CheckCircle size={12} /> Added to {project.studentName}'s to-do list.</p>
        )}
      </div>

      <GuideFeedbackPanel projectId={project.projectId} editable={true} />
      <ProgressUpdateFeed projectId={project.projectId} canPost={false} />
      <DiscussionThread projectId={project.projectId} />
    </div>
  );
};

export default ProjectDiscussion;
