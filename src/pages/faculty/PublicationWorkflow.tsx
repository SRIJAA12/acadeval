import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAllProjects } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import { Award, BookOpen, ExternalLink, Sparkles, CheckCircle2, ChevronRight, Filter } from 'lucide-react';
import type { ProjectSummary } from '../../types';
import clsx from 'clsx';

const PublicationWorkflow: React.FC = () => {
  const navigate = useNavigate();
  const [selectedDomain, setSelectedDomain] = useState<string>('All');
  const [nominatedIds, setNominatedIds] = useState<Set<string>>(new Set());

  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['allProjects'],
    queryFn: getAllProjects,
  });

  if (isLoading) return <LoadingState message="Loading publication potential projects..." />;
  if (isError) return <ErrorState retry={refetch} />;

  // Filter projects with score >= 75 or already reviewed
  const candidateProjects = (projects || []).filter(p => {
    const matchesDomain = selectedDomain === 'All' || p.domain === selectedDomain;
    const isHighQuality = (p.overallScore !== null && p.overallScore >= 70) || p.pipelineStatus === 'reviewed';
    return matchesDomain && isHighQuality;
  });

  const domains = ['All', ...Array.from(new Set((projects || []).map(p => p.domain)))];

  const handleNominate = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setNominatedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900 flex items-center gap-2">
            <Award className="text-gold-500" size={26} /> Publication Candidates & Workflow
          </h1>
          <p className="text-slate-500 mt-1">
            Identify high-novelty capstone projects eligible for IEEE / ACM conference and journal submissions.
          </p>
        </div>

        {/* Domain Filter */}
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-slate-400" />
          <select
            value={selectedDomain}
            onChange={(e) => setSelectedDomain(e.target.value)}
            className="input-field text-sm py-1.5 px-3 bg-white border border-slate-200 rounded-lg shadow-sm"
          >
            {domains.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>

      {candidateProjects.length === 0 ? (
        <EmptyState
          icon={<BookOpen size={32} />}
          title="No publication candidates found"
          description="Projects with an evaluation score of 70+ or high novelty will automatically qualify as publication candidates."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {candidateProjects.map(p => {
            const isNominated = nominatedIds.has(p.projectId);
            return (
              <div
                key={p.projectId}
                onClick={() => navigate(`/faculty/project/${p.projectId}`)}
                className={clsx(
                  'card-hover cursor-pointer border rounded-2xl p-5 flex flex-col justify-between transition-all',
                  isNominated ? 'border-teal-500 bg-teal-50/20' : 'border-slate-200 bg-white'
                )}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <Badge type="domain" value={p.domain} size="sm" />
                    <span className={clsx(
                      'text-xs font-bold px-2 py-0.5 rounded-full',
                      (p.overallScore || 0) >= 80 ? 'bg-teal-100 text-teal-800' : 'bg-gold-100 text-gold-800'
                    )}>
                      Score: {p.overallScore ?? 'N/A'}/100
                    </span>
                  </div>

                  <h3 className="font-semibold text-navy-900 text-base line-clamp-2 mb-2">{p.title}</h3>
                  <p className="text-xs text-slate-500 mb-4">
                    Student: <span className="font-medium text-slate-700">{p.studentName}</span> ({p.rollNo})
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Target Track</span>
                    <span className="font-medium text-navy-800">IEEE / Scopus Indexed</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => handleNominate(p.projectId, e)}
                      className={clsx(
                        'btn text-xs py-1.5 flex-1 flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all',
                        isNominated
                          ? 'bg-teal-600 text-white hover:bg-teal-700 shadow-sm'
                          : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      )}
                    >
                      {isNominated ? (
                        <>
                          <CheckCircle2 size={14} /> Nominated for Review
                        </>
                      ) : (
                        <>
                          <Sparkles size={14} className="text-gold-500" /> Nominate for Publication
                        </>
                      )}
                    </button>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/faculty/project/${p.projectId}`);
                      }}
                      className="p-1.5 text-slate-400 hover:text-navy-700 hover:bg-slate-100 rounded-lg transition-colors"
                      title="View Report"
                    >
                      <ChevronRight size={18} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PublicationWorkflow;
