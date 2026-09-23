import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAllProjects } from '../../api/endpoints';
import { LoadingState, ErrorState, EmptyState } from '../../components/States';
import Badge from '../../components/Badge';
import {
  FolderGit2, Search, Filter, ChevronRight, Eye, CheckCircle, Clock,
  Cpu, Award, Download
} from 'lucide-react';
import type { ProjectSummary } from '../../types';
import clsx from 'clsx';

const HODProjectList: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');

  const { data: projects, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-all-projects'],
    queryFn: getAllProjects,
  });

  if (isLoading) return <LoadingState message="Loading department submissions..." />;
  if (isError) return <ErrorState retry={refetch} />;

  const allProjects = projects || [];

  // Extract unique domains
  const domains = Array.from(new Set(allProjects.map(p => p.domain).filter(Boolean)));

  // Filter projects
  const filteredProjects = allProjects.filter(p => {
    const matchesSearch =
      searchTerm === '' ||
      p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.studentName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.rollNo.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesDomain = selectedDomain === 'all' || p.domain === selectedDomain;
    const matchesStatus = selectedStatus === 'all' || p.pipelineStatus === selectedStatus;

    return matchesSearch && matchesDomain && matchesStatus;
  });

  const reviewedCount = allProjects.filter(p => p.pipelineStatus === 'reviewed').length;
  const pendingCount = allProjects.filter(p => p.pipelineStatus === 'awaiting_review').length;
  const scores = allProjects.map(p => p.overallScore).filter((s): s is number => s !== null && s > 0);
  const avgScore = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : 'N/A';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900 flex items-center gap-2">
            <FolderGit2 className="text-gold-500" /> Department Submissions
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Complete registry of student project submissions, evaluation status, and audit records
          </p>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card py-4 px-5">
          <p className="text-xs text-slate-500 font-medium">Total Submissions</p>
          <p className="text-2xl font-bold font-display text-navy-900 mt-1">{allProjects.length}</p>
        </div>
        <div className="card py-4 px-5">
          <p className="text-xs text-slate-500 font-medium">Awaiting Faculty Review</p>
          <p className="text-2xl font-bold font-display text-amber-600 mt-1">{pendingCount}</p>
        </div>
        <div className="card py-4 px-5">
          <p className="text-xs text-slate-500 font-medium">Published & Finalized</p>
          <p className="text-2xl font-bold font-display text-teal-600 mt-1">{reviewedCount}</p>
        </div>
        <div className="card py-4 px-5">
          <p className="text-xs text-slate-500 font-medium">Department Avg Score</p>
          <p className="text-2xl font-bold font-display text-gold-600 mt-1">{avgScore}</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-2.5 text-slate-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Search by title, student name, or roll no..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-gold-500 outline-none"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={selectedDomain}
            onChange={e => setSelectedDomain(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-xs rounded-xl px-3 py-2 outline-none font-medium text-slate-700"
          >
            <option value="all">All Domains</option>
            {domains.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>

          <select
            value={selectedStatus}
            onChange={e => setSelectedStatus(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-xs rounded-xl px-3 py-2 outline-none font-medium text-slate-700"
          >
            <option value="all">All Statuses</option>
            <option value="uploaded">Uploaded</option>
            <option value="ai_processing">AI Processing</option>
            <option value="awaiting_review">Awaiting Review</option>
            <option value="reviewed">Reviewed / Published</option>
          </select>
        </div>
      </div>

      {/* Projects Table */}
      {filteredProjects.length === 0 ? (
        <EmptyState
          icon={<FolderGit2 size={28} />}
          title="No projects match the criteria"
          description="Try adjusting your search query or domain filter."
        />
      ) : (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Project Title</th>
                  <th className="py-3.5 px-4">Student</th>
                  <th className="py-3.5 px-4">Domain</th>
                  <th className="py-3.5 px-4">Submitted On</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-center">Score</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredProjects.map(project => (
                  <tr
                    key={project.projectId}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    onClick={() => navigate(`/hod/report/${project.projectId}`)}
                  >
                    <td className="py-3.5 px-4 font-medium text-navy-900 max-w-xs truncate">
                      {project.title}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-800">{project.studentName}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{project.rollNo}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge type="domain" value={project.domain} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {new Date(project.submittedOn).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge type="pipeline" value={project.pipelineStatus} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {project.overallScore !== null ? (
                        <span className={clsx(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold',
                          project.overallScore >= 80 ? 'bg-teal-50 text-teal-700' :
                          project.overallScore >= 60 ? 'bg-gold-50 text-gold-700' : 'bg-red-50 text-red-700'
                        )}>
                          {project.overallScore}
                        </span>
                      ) : (
                        <span className="text-slate-400 font-medium">—</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/hod/report/${project.projectId}`);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-gold-50 hover:bg-gold-100 text-gold-700 rounded-lg font-medium transition text-xs"
                      >
                        <Eye size={13} /> View Report
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default HODProjectList;
