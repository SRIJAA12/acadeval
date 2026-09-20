import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Video, FileSearch, GitBranch, AlertCircle, CheckCircle, Loader2, ChevronRight } from 'lucide-react';
import FileUploader from '../../components/FileUploader';
import { uploadProject } from '../../api/endpoints';
import { useAuth } from '../../auth/AuthContext';
import clsx from 'clsx';

type UploadMode = 'document' | 'video' | 'abstract';

const abstractSchema = z.object({
  title: z.string().min(5, 'Title must be at least 5 characters'),
  domain: z.string().min(1, 'Please select a domain'),
  teamMembers: z.string().min(1, 'Please enter team member names'),
  abstract: z.string()
    .refine(value => value.trim().split(/\s+/).filter(Boolean).length >= 150, 'Abstract must be at least 150 words')
    .refine(value => value.trim().split(/\s+/).filter(Boolean).length <= 500, 'Abstract cannot exceed 500 words'),
  relatedSubmissionId: z.string().optional(),
});

type AbstractFormData = z.infer<typeof abstractSchema>;

const DOMAINS = ['AI/ML', 'IoT', 'Web/App', 'Cybersecurity', 'Healthcare', 'Agriculture', 'Smart Systems', 'Education'];

const MODES: { id: UploadMode; icon: React.ReactNode; label: string; description: string }[] = [
  { id: 'document', icon: <FileText size={20} />, label: 'Full Document', description: 'PDF, DOCX, PPTX + GitHub URL' },
  { id: 'video', icon: <Video size={20} />, label: 'Video Presentation', description: 'MP4/MOV + optional slides' },
  { id: 'abstract', icon: <FileSearch size={20} />, label: 'Abstract Only', description: 'Quick pre-check (novelty, feasibility)' },
];

const Upload: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<UploadMode>('document');
  const [projectTitle, setProjectTitle] = useState('');
  const [projectDomain, setProjectDomain] = useState('AI/ML');
  const [githubUrl, setGithubUrl] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<AbstractFormData>({
    resolver: zodResolver(abstractSchema),
  });

  const abstractText = watch('abstract', '');
  const wordCount = abstractText ? abstractText.trim().split(/\s+/).filter(Boolean).length : 0;

  const invalidateAndSetSubmitted = () => {
    queryClient.invalidateQueries({ queryKey: ['myProjects'] });
    queryClient.invalidateQueries({ queryKey: ['myReports'] });
    setSubmitted(true);
  };

  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append('mode', mode);
      fd.append('domain', projectDomain);
      if (projectTitle) fd.append('title', projectTitle);
      uploadedFiles.forEach(f => fd.append('files', f));
      if (githubUrl) fd.append('githubUrl', githubUrl);
      return uploadProject(fd);
    },
    onSuccess: invalidateAndSetSubmitted,
  });

  const onAbstractSubmit = (data: AbstractFormData) => {
    const fd = new FormData();
    fd.append('mode', 'abstract');
    fd.append('title', data.title);
    fd.append('domain', data.domain);
    fd.append('teamMembers', data.teamMembers);
    fd.append('abstract', data.abstract);
    uploadProject(fd).then(invalidateAndSetSubmitted);
  };

  if (submitted) {
    return (
      <div className="max-w-lg mx-auto mt-12">
        <div className="card text-center py-12">
          <div className="w-20 h-20 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={36} className="text-teal-500" />
          </div>
          <h2 className="text-2xl font-display font-bold text-navy-900 mb-2">Submission Received!</h2>
          <p className="text-slate-500 mb-2">Your project has been submitted for AI processing.</p>
          <div className="bg-teal-50 rounded-xl p-4 border border-teal-100 text-sm text-teal-700 mb-6">
            <p className="font-semibold mb-1">What happens next?</p>
            <p>The AI pipeline will process your submission and generate an evaluation report within a few minutes. Your guide will then review and publish the final report.</p>
          </div>
          <div className="flex gap-3 justify-center">
            <button onClick={() => navigate('/student/reports')} className="btn-primary">
              View My Reports <ChevronRight size={16} />
            </button>
            <button onClick={() => setSubmitted(false)} className="btn-outline">Submit Another</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Submit Project</h1>
        <p className="text-slate-500 mt-1">Upload your project for AI-powered evaluation</p>
      </div>

      {/* Mode Selector */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        {MODES.map(m => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={clsx(
              'p-4 rounded-2xl border-2 text-left transition-all duration-150',
              mode === m.id
                ? 'border-teal-500 bg-teal-50'
                : 'border-slate-100 bg-white hover:border-teal-200'
            )}
          >
            <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center mb-3',
              mode === m.id ? 'bg-teal-500 text-white' : 'bg-slate-100 text-slate-500'
            )}>
              {m.icon}
            </div>
            <p className={clsx('font-semibold text-sm', mode === m.id ? 'text-teal-700' : 'text-slate-700')}>{m.label}</p>
            <p className="text-xs text-slate-400 mt-0.5">{m.description}</p>
          </button>
        ))}
      </div>

      {/* Document Mode */}
      {mode === 'document' && (
        <div className="card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-navy-900 mb-1">Full Document Submission</h2>
            <p className="text-sm text-slate-500">Upload your project report, slides, and optionally link your GitHub repository.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Project Title (optional)</label>
              <input
                type="text"
                value={projectTitle}
                onChange={e => setProjectTitle(e.target.value)}
                className="input"
                placeholder="e.g. AI-Based Smart Attendance System"
              />
            </div>
            <div>
              <label className="label">Domain</label>
              <select
                value={projectDomain}
                onChange={e => setProjectDomain(e.target.value)}
                className="input"
              >
                {DOMAINS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <FileUploader
            accept={['.pdf', '.docx', '.pptx']}
            multiple
            maxSize={50}
            onFilesSelected={setUploadedFiles}
            label="Drop your project files here"
            hint="PDF, DOCX, PPTX · Max 50MB per file · You can attach report + slides"
          />

          <div>
            <label className="label flex items-center gap-2"><GitBranch size={15} /> GitHub Repository URL (optional)</label>
            <input
              type="url"
              value={githubUrl}
              onChange={e => setGithubUrl(e.target.value)}
              className="input"
              placeholder="https://github.com/username/project-repo"
            />
          </div>

          {mutation.isError && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-4 py-3 rounded-xl">
              <AlertCircle size={16} /> {(mutation.error as any)?.response?.data?.detail || 'Upload failed. Please ensure you are logged in as a student and try again.'}
            </div>
          )}

          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || uploadedFiles.length === 0}
            className="btn-primary w-full justify-center py-3"
          >
            {mutation.isPending ? <><Loader2 size={16} className="animate-spin" /> Processing...</> : 'Submit for Evaluation'}
          </button>
        </div>
      )}

      {/* Video Mode */}
      {mode === 'video' && (
        <div className="card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-navy-900 mb-1">Video Presentation Submission</h2>
            <p className="text-sm text-slate-500">Your video will be transcribed using Whisper, then evaluated through the same pipeline.</p>
          </div>

          <div className="bg-gold-50 rounded-xl p-4 border border-gold-100">
            <p className="text-sm text-gold-700 font-medium">💡 Video tips:</p>
            <ul className="text-xs text-gold-600 mt-1 space-y-1 list-disc list-inside">
              <li>MP4 or MOV format, up to 500MB</li>
              <li>Ensure audio is clear for accurate transcription</li>
              <li>Optionally attach PPTX slides for slide analysis</li>
            </ul>
          </div>

          <FileUploader
            accept={['.mp4', '.mov']}
            multiple={false}
            maxSize={500}
            onFilesSelected={files => setUploadedFiles(files)}
            label="Drop your presentation video here"
            hint="MP4 or MOV · Max 500MB · Whisper transcription will be applied"
          />

          <FileUploader
            accept={['.pptx']}
            multiple={false}
            maxSize={20}
            onFilesSelected={files => setUploadedFiles(prev => [...prev, ...files])}
            label="Slides (optional)"
            hint="PPTX format for slide analysis"
          />

          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || uploadedFiles.length === 0}
            className="btn-primary w-full justify-center py-3"
          >
            {mutation.isPending ? <><Loader2 size={16} className="animate-spin" /> Uploading...</> : 'Submit Video for Evaluation'}
          </button>
        </div>
      )}

      {/* Abstract Mode */}
      {mode === 'abstract' && (
        <form onSubmit={handleSubmit(onAbstractSubmit)} className="card space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-navy-900 mb-1">Abstract Pre-Check</h2>
            <p className="text-sm text-slate-500">A quick novelty and feasibility screening. Domain screening, similarity flagging, and a partial evaluation report will be generated.</p>
          </div>

          <div className="bg-navy-50 rounded-xl p-4 border border-navy-200">
            <p className="text-xs text-navy-900 font-medium">⚠ Partial Evaluation Notice</p>
            <p className="text-xs text-navy-700 mt-1">Abstract-only evaluations do not include completeness, citation, or presentation critique scores. A full submission can be linked later.</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Project Title *</label>
              <input {...register('title')} className={`input ${errors.title ? 'input-error' : ''}`} placeholder="e.g. AI-Based Crop Disease Detection System" />
              {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title.message}</p>}
            </div>
            <div>
              <label className="label">Domain *</label>
              <select {...register('domain')} className={`input ${errors.domain ? 'input-error' : ''}`}>
                <option value="">Select domain...</option>
                {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
              {errors.domain && <p className="text-xs text-red-500 mt-1">{errors.domain.message}</p>}
            </div>
            <div>
              <label className="label">Team Members *</label>
              <input {...register('teamMembers')} className="input" placeholder="e.g. Member one, Member two" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">Abstract *</label>
              <span className={clsx('text-xs', wordCount < 150 ? 'text-red-500' : wordCount > 500 ? 'text-orange-500' : 'text-teal-600')}>
                {wordCount} / 150–500 words
              </span>
            </div>
            <textarea
              {...register('abstract')}
              rows={10}
              className={`input resize-none ${errors.abstract ? 'input-error' : ''}`}
              placeholder="Paste your project abstract here (150–500 words)..."
            />
            {errors.abstract && <p className="text-xs text-red-500 mt-1">{errors.abstract.message}</p>}
          </div>

          <div>
            <label className="label">Link to Previous Submission (optional)</label>
            <input
              {...register('relatedSubmissionId')}
              className="input"
              placeholder="Submission ID from a previous upload (to link abstract → full doc)"
            />
          </div>

          <button type="submit" className="btn-primary w-full justify-center py-3">
            Submit Abstract for Pre-Check
          </button>
        </form>
      )}
    </div>
  );
};

export default Upload;
