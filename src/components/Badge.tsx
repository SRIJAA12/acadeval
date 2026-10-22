import React from 'react';
import clsx from 'clsx';
import {
  Trophy, FileText, Video, FileSearch, Clock, Cpu,
  CheckCircle, AlertCircle, Star, Zap, Award, BookOpen,
  TrendingUp, Shield, XCircle,
} from 'lucide-react';
import type { PipelineStatus, SubmissionType, FeasibilityRating, NoveltyVerdict, AppealStatus } from '../types';

type BadgeType =
  | 'pipeline'
  | 'submission'
  | 'feasibility'
  | 'novelty'
  | 'appeal'
  | 'achievement'
  | 'domain'
  | 'score';

interface BadgeProps {
  type: BadgeType;
  value: string;
  size?: 'sm' | 'md';
}

const pipelineConfig: Record<PipelineStatus, { label: string; className: string; icon: React.ReactNode }> = {
  uploaded: { label: 'Uploaded', className: 'badge-slate', icon: <FileText size={11} /> },
  ai_processing: { label: 'AI Processing', className: 'badge-navy', icon: <Cpu size={11} /> },
  awaiting_review: { label: 'Awaiting Review', className: 'badge-orange', icon: <Clock size={11} /> },
  reviewed: { label: 'Reviewed', className: 'badge-teal', icon: <CheckCircle size={11} /> },
  failed: { label: 'Failed', className: 'badge-red', icon: <XCircle size={11} /> },
};

const submissionConfig: Record<SubmissionType, { label: string; className: string; icon: React.ReactNode }> = {
  document: { label: 'Document', className: 'badge-navy', icon: <FileText size={11} /> },
  journal: { label: 'Journal', className: 'badge-gold', icon: <BookOpen size={11} /> },
  abstract: { label: 'Abstract', className: 'badge-slate', icon: <FileSearch size={11} /> },
  video: { label: 'Video', className: 'badge-purple', icon: <Video size={11} /> },
};

const feasibilityConfig: Record<FeasibilityRating, { className: string }> = {
  High: { className: 'badge-teal' },
  Medium: { className: 'badge-gold' },
  Low: { className: 'badge-red' },
};

const noveltyConfig: Record<NoveltyVerdict, { className: string; icon: React.ReactNode }> = {
  Common: { className: 'badge-slate', icon: <BookOpen size={11} /> },
  'Somewhat Novel': { className: 'badge-gold', icon: <TrendingUp size={11} /> },
  Novel: { className: 'badge-teal', icon: <Star size={11} /> },
};

const appealConfig: Record<AppealStatus, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'badge-orange' },
  under_review: { label: 'Under Review', className: 'badge-navy' },
  resolved: { label: 'Resolved', className: 'badge-teal' },
  rejected: { label: 'Rejected', className: 'badge-red' },
};

const achievementIcons: Record<string, React.ReactNode> = {
  'Novel Idea Award': <Star size={11} />,
  'Publication Ready': <Award size={11} />,
  'Most Improved': <TrendingUp size={11} />,
  'High Feasibility': <Zap size={11} />,
  'Top Scorer 2025': <Trophy size={11} />,
};

const Badge: React.FC<BadgeProps> = ({ type, value, size = 'md' }) => {
  const textClass = size === 'sm' ? 'text-[10px]' : 'text-xs';

  if (type === 'pipeline') {
    const cfg = pipelineConfig[value as PipelineStatus] || { label: value, className: 'badge-slate', icon: null };
    return <span className={clsx('badge', cfg.className, textClass)}>{cfg.icon}{cfg.label}</span>;
  }

  if (type === 'submission') {
    const cfg = submissionConfig[value as SubmissionType] || { label: value, className: 'badge-slate', icon: null };
    return <span className={clsx('badge', cfg.className, textClass)}>{cfg.icon}{cfg.label}</span>;
  }

  if (type === 'feasibility') {
    const cfg = feasibilityConfig[value as FeasibilityRating] || { className: 'badge-slate' };
    return <span className={clsx('badge', cfg.className, textClass)}><Zap size={11} />{value} Feasibility</span>;
  }

  if (type === 'novelty') {
    const cfg = noveltyConfig[value as NoveltyVerdict] || { className: 'badge-slate', icon: null };
    return <span className={clsx('badge', cfg.className, textClass)}>{cfg.icon}{value}</span>;
  }

  if (type === 'appeal') {
    const cfg = appealConfig[value as AppealStatus] || { label: value, className: 'badge-slate' };
    return <span className={clsx('badge', cfg.className, textClass)}>{cfg.label}</span>;
  }

  if (type === 'achievement') {
    const icon = achievementIcons[value] || <Trophy size={11} />;
    return <span className={clsx('badge badge-gold', textClass)}>{icon}{value}</span>;
  }

  if (type === 'domain') {
    const domainColors: Record<string, string> = {
      'AI/ML': 'badge-teal',
      'IoT': 'badge-navy',
      'Web/App': 'badge-purple',
      'Healthcare': 'badge-red',
      'Cybersecurity': 'badge-orange',
      'Agriculture': 'badge-teal',
      'Smart Systems': 'badge-navy',
    };
    return <span className={clsx('badge', domainColors[value] || 'badge-slate', textClass)}>{value}</span>;
  }

  return <span className={clsx('badge badge-slate', textClass)}>{value}</span>;
};

export default Badge;
