import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getHODStats } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import { TrendChart } from '../../components/Charts';
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { Users, GraduationCap, FileText, CheckCircle, TrendingUp, History, FolderGit2, ChevronRight } from 'lucide-react';

ChartJS.register(ArcElement, Tooltip, Legend);

const DOMAIN_COLORS = [
  '#1E7F72', '#C99A3A', '#1B2A4A', '#3b82f6', '#8b5cf6', '#ef4444', '#f97316',
];

const DeptOverview: React.FC = () => {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hodStats'],
    queryFn: getHODStats,
  });

  if (isLoading) return <LoadingState message="Loading department overview..." />;
  if (isError || !data) return <ErrorState retry={refetch} />;

  const domainLabels = Object.keys(data.domainDistribution || {});
  const domainValues = Object.values(data.domainDistribution || {});

  const doughnutData = {
    labels: domainLabels,
    datasets: [{
      data: domainValues,
      backgroundColor: DOMAIN_COLORS,
      borderColor: '#ffffff',
      borderWidth: 3,
      hoverBorderWidth: 4,
    }],
  };

  const doughnutOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'right' as const,
        labels: { font: { family: 'Inter', size: 12 }, color: '#475569', padding: 16, boxWidth: 12 },
      },
      tooltip: {
        backgroundColor: '#1B2A4A',
        callbacks: {
          label: (ctx: { label: string; raw: unknown }) =>
            ` ${ctx.label}: ${ctx.raw} projects`,
        },
      },
    },
  };

  const reviewedPct = data.totalSubmissions > 0
    ? Math.round((data.reviewedCount / data.totalSubmissions) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-navy-900">Department Overview</h1>
          <p className="text-slate-500 mt-1">Aggregate statistics, quality benchmarks, and audit logs across all faculty and students</p>
        </div>
        <button
          onClick={() => navigate('/hod/projects')}
          className="btn-primary flex items-center gap-2 self-start md:self-auto"
        >
          <FolderGit2 size={16} /> View All Submissions <ChevronRight size={14} />
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { icon: <GraduationCap size={22} className="text-teal-600" />, label: 'Students', value: data.totalStudents, color: 'bg-teal-50' },
          { icon: <Users size={22} className="text-gold-600" />, label: 'Faculty', value: data.totalFaculty, color: 'bg-gold-50' },
          { icon: <FileText size={22} className="text-navy-700" />, label: 'Submissions', value: data.totalSubmissions, color: 'bg-navy-50' },
          { icon: <CheckCircle size={22} className="text-teal-600" />, label: 'Reviewed', value: `${reviewedPct}%`, color: 'bg-teal-50' },
          { icon: <TrendingUp size={22} className="text-purple-600" />, label: 'Avg Score', value: `${(data.avgScore || 0).toFixed(1)}`, color: 'bg-purple-50' },
        ].map(stat => (
          <div key={stat.label} className="card text-center py-5">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center mx-auto mb-2 ${stat.color}`}>
              {stat.icon}
            </div>
            <p className="text-2xl font-display font-bold text-navy-900">{stat.value}</p>
            <p className="text-xs text-slate-400 mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Domain Distribution */}
        <div className="card">
          <h2 className="font-semibold text-navy-900 mb-5">Domain Distribution</h2>
          {domainLabels.length > 0 ? (
            <div style={{ height: 280 }}>
              <Doughnut data={doughnutData} options={doughnutOptions} />
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-400 text-sm">
              No submissions categorized yet.
            </div>
          )}
        </div>

        {/* Score Trend */}
        <div className="card">
          <h2 className="font-semibold text-navy-900 mb-5">Evaluation Score Trends</h2>
          {data.trendData && data.trendData.length > 0 ? (
            <TrendChart data={data.trendData} title="" />
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-slate-400 text-sm">
              <TrendingUp size={28} className="text-slate-300 mb-2" />
              <span>No historical evaluation trend data available yet.</span>
              <span className="text-xs text-slate-400 mt-1">Trends will populate as faculty complete reviews.</span>
            </div>
          )}
        </div>
      </div>

      {/* Review Progress */}
      <div className="card">
        <h2 className="font-semibold text-navy-900 mb-4">Review Progress This Semester</h2>
        <div className="flex items-center gap-4 mb-3">
          <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
            <div
              className="bg-teal-500 h-4 rounded-full transition-all duration-1000"
              style={{ width: `${reviewedPct}%` }}
            />
          </div>
          <span className="text-lg font-bold text-teal-700">{reviewedPct}%</span>
        </div>
        <p className="text-sm text-slate-500">
          <strong>{data.reviewedCount}</strong> of <strong>{data.totalSubmissions}</strong> submissions have been finalized.
          {data.totalSubmissions - data.reviewedCount > 0 ? ` ${data.totalSubmissions - data.reviewedCount} remain in review.` : ' All submissions up to date.'}
        </p>
      </div>

      {/* Score Override Audit Trail */}
      {data.recentOverrides && data.recentOverrides.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-navy-900 flex items-center gap-2">
              <History size={18} className="text-gold-500" /> Recent Faculty Score Overrides (Audit Log)
            </h2>
            <span className="text-xs text-slate-400">{data.recentOverrides.length} records</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Faculty Reviewer</th>
                  <th className="py-2.5 px-3">Dimension</th>
                  <th className="py-2.5 px-3 text-center">AI Score</th>
                  <th className="py-2.5 px-3 text-center">New Score</th>
                  <th className="py-2.5 px-3">Rationale / Justification</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.recentOverrides.map(ov => (
                  <tr key={ov.id} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                      {ov.timestamp ? new Date(ov.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—'}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-800">{ov.changedByName}</td>
                    <td className="py-2.5 px-3 capitalize font-medium text-slate-600">{ov.dimension}</td>
                    <td className="py-2.5 px-3 text-center font-mono text-slate-500">{ov.oldValue}</td>
                    <td className="py-2.5 px-3 text-center font-mono font-bold text-teal-700">{ov.newValue}</td>
                    <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate">{ov.comment}</td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => navigate(`/hod/report/${ov.projectId}`)}
                        className="text-gold-600 hover:text-gold-700 font-medium"
                      >
                        Inspect
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

export default DeptOverview;

