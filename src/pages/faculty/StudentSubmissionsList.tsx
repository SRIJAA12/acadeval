import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAllProjects } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import { Search, SlidersHorizontal, ChevronRight, Users } from 'lucide-react';
import type { PipelineStatus, SubmissionType } from '../../types';
import clsx from 'clsx';

const StudentSubmissionsList: React.FC = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<PipelineStatus | ''>('');
  const [filterType, setFilterType] = useState<SubmissionType | ''>('');
  const [filterDomain, setFilterDomain] = useState('');
  const [sortBy, setSortBy] = useState<'submittedOn' | 'overallScore'>('submittedOn');

  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['allProjects'],
    queryFn: getAllProjects,
  });

  const filtered = (projects || [])
    .filter(p =>
      (search === '' || p.studentName.toLowerCase().includes(search.toLowerCase()) || p.title.toLowerCase().includes(search.toLowerCase()) || p.rollNo.includes(search)) &&
      (filterStatus === '' || p.pipelineStatus === filterStatus) &&
      (filterType === '' || p.submissionType === filterType) &&
      (filterDomain === '' || p.domain === filterDomain)
    )
    .sort((a, b) => {
      if (sortBy === 'overallScore') {
        return (b.overallScore ?? -1) - (a.overallScore ?? -1);
      }
      return new Date(b.submittedOn).getTime() - new Date(a.submittedOn).getTime();
    });

  if (isLoading) return <LoadingState message="Loading submissions..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">All Submissions</h1>
        <p className="text-slate-500 mt-1">All student project documents assigned to you</p>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-60">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search student, title, roll no..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input pl-9"
            />
          </div>

          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value as PipelineStatus | '')} className="input w-auto">
            <option value="">All Statuses</option>
            <option value="uploaded">Uploaded</option>
            <option value="ai_processing">AI Processing</option>
            <option value="awaiting_review">Awaiting Review</option>
            <option value="reviewed">Reviewed</option>
          </select>

          <select value={filterType} onChange={e => setFilterType(e.target.value as SubmissionType | '')} className="input w-auto">
            <option value="">All Types</option>
            <option value="document">Document</option>
            <option value="journal">Journal</option>
            <option value="abstract">Abstract</option>
            <option value="video">Video (legacy)</option>
          </select>

          <select value={filterDomain} onChange={e => setFilterDomain(e.target.value)} className="input w-auto">
            <option value="">All Domains</option>
            {['AI/ML', 'IoT', 'Web/App', 'Healthcare', 'Cybersecurity', 'Agriculture', 'Smart Systems'].map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>

          <select value={sortBy} onChange={e => setSortBy(e.target.value as typeof sortBy)} className="input w-auto">
            <option value="submittedOn">Sort: Date</option>
            <option value="overallScore">Sort: Score</option>
          </select>

          <div className="flex items-center gap-2 text-sm text-slate-500">
            <SlidersHorizontal size={15} />
            {filtered.length} results
          </div>
        </div>
      </div>

      {!filtered.length ? (
        <EmptyState icon={<Users size={28} />} title="No submissions match your filters" description="Try adjusting the filters above" />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Project Title</th>
                <th>Type</th>
                <th>Domain</th>
                <th>Submitted</th>
                <th>Status</th>
                <th>AI Score</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr
                  key={p.projectId}
                  className="cursor-pointer"
                  onClick={() => navigate(`/faculty/report/${p.projectId}`)}
                >
                  <td>
                    <div>
                      <p className="font-medium text-slate-800">{p.studentName}</p>
                      <p className="text-xs text-slate-400">{p.rollNo}</p>
                    </div>
                  </td>
                  <td>
                    <p className="text-slate-700 text-sm max-w-xs" title={p.title}>{p.title}</p>
                  </td>
                  <td><Badge type="submission" value={p.submissionType} size="sm" /></td>
                  <td><Badge type="domain" value={p.domain} size="sm" /></td>
                  <td>
                    <span className="text-sm text-slate-500">
                      {new Date(p.submittedOn).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </span>
                  </td>
                  <td><Badge type="pipeline" value={p.pipelineStatus} size="sm" /></td>
                  <td>
                    {p.overallScore !== null ? (
                      <span className={clsx(
                        'font-bold text-sm',
                        p.overallScore >= 80 ? 'text-teal-600' : p.overallScore >= 60 ? 'text-gold-500' : 'text-red-500'
                      )}>
                        {p.overallScore}
                      </span>
                    ) : (
                      <span className="text-slate-300 text-sm">—</span>
                    )}
                  </td>
                  <td>
                    <ChevronRight size={16} className="text-slate-300" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default StudentSubmissionsList;
