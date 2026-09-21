import React, { useEffect, useState, useMemo } from 'react';
import {
  Share2, RefreshCw, Cpu, Network, ShieldCheck, Activity, AlertCircle
} from 'lucide-react';
import { ProjectGraphViewer } from '../../components/ProjectGraphViewer';
import { getAllProjects, getGraphSummary, getGraphVisualization, rebuildKnowledgeGraph } from '../../api/endpoints';

export const GraphExplorerView: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [allProjectsList, setAllProjectsList] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [rebuilding, setRebuilding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, vizRes, projListRes] = await Promise.all([
        getGraphSummary(true),
        getGraphVisualization(400),
        getAllProjects(),
      ]);
      setSummary(sumRes?.metrics || null);
      setAllProjectsList(projListRes || []);
      setGraphData({
        nodes: vizRes?.nodes || [],
        links: vizRes?.links || [],
      });
    } catch (err: any) {
      console.error('Failed to load Knowledge Graph data:', err);
      setError(err?.message || 'Failed to load Knowledge Graph. Ensure backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filter graph nodes & edges by selected project (include target Project node + ALL connected entity neighbors)
  const { displayNodes, displayLinks } = useMemo(() => {
    if (selectedProjectId === 'all' || !selectedProjectId) {
      return { displayNodes: graphData.nodes, displayLinks: graphData.links };
    }

    const targetProj = allProjectsList.find(p => p.projectId === selectedProjectId);
    const shortId = selectedProjectId.substring(0, 8);
    const titleSnippet = targetProj?.title ? targetProj.title.substring(0, 15).toLowerCase() : '';

    // Find the project node by UUID prefix or title snippet
    const projNode = graphData.nodes.find(n =>
      n.type === 'Project' && (
        n.name.includes(shortId) ||
        (titleSnippet && n.name.toLowerCase().includes(titleSnippet))
      )
    );

    if (!projNode) {
      return { displayNodes: graphData.nodes, displayLinks: graphData.links };
    }

    // Find all links attached to this project node
    const projLinks = graphData.links.filter(l => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      const tId = typeof l.target === 'object' ? l.target.id : l.target;
      return sId === projNode.id || tId === projNode.id;
    });

    const neighborIds = new Set<string | number>([projNode.id]);
    projLinks.forEach(l => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      const tId = typeof l.target === 'object' ? l.target.id : l.target;
      neighborIds.add(sId);
      neighborIds.add(tId);
    });

    // Also include co-occurrence links between these connected entities
    const allSubLinks = graphData.links.filter(l => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      const tId = typeof l.target === 'object' ? l.target.id : l.target;
      return neighborIds.has(sId) && neighborIds.has(tId);
    });

    const subNodes = graphData.nodes.filter(n => neighborIds.has(n.id));
    return { displayNodes: subNodes, displayLinks: allSubLinks };
  }, [selectedProjectId, graphData, allProjectsList]);

  const handleRebuild = async () => {
    if (!window.confirm('Rebuild Knowledge Graph from all project submissions in PostgreSQL?')) return;
    setRebuilding(true);
    try {
      const res = await rebuildKnowledgeGraph();
      setToastMessage(`Graph rebuilt successfully: ${res?.result?.projects_processed || 0} projects, ${res?.result?.relational_nodes || 0} nodes.`);
      await fetchData();
    } catch (err: any) {
      alert('Failed to rebuild graph: ' + (err?.message || err));
    } finally {
      setRebuilding(false);
      setTimeout(() => setToastMessage(null), 5000);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs uppercase tracking-wider">
            <Network className="w-4 h-4" /> Module 4 — Project Knowledge Graph Construction
          </div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            Knowledge Graph Explorer
            <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono px-2.5 py-1 rounded-full font-normal">
              NetworkX MultiDiGraph
            </span>
          </h1>
          <p className="text-xs text-slate-400 max-w-2xl">
            Visualise and inspect the relational project graph. Each project node is linked to its domain, algorithms, technologies, frameworks, datasets, applications, and metrics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <label className="text-[10px] text-slate-400 font-semibold uppercase mb-1">Filter by Project</label>
            <select
              value={selectedProjectId}
              onChange={e => setSelectedProjectId(e.target.value)}
              className="bg-slate-800 text-slate-200 border border-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="all">🌐 All Projects Combined Subgraph</option>
              {allProjectsList.map(p => (
                <option key={p.projectId} value={p.projectId}>
                  📁 {p.title.length > 35 ? p.title.substring(0, 35) + '...' : p.title} ({p.studentName})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={fetchData}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition flex items-center gap-2 disabled:opacity-50 mt-4"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>

          <button
            onClick={handleRebuild}
            disabled={rebuilding || loading}
            className="px-3.5 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-xs font-medium rounded-xl border border-indigo-600 transition flex items-center gap-2 disabled:opacity-50 mt-4"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            {rebuilding ? 'Rebuilding…' : 'Rebuild scored graph'}
          </button>
        </div>
      </div>

      {toastMessage && (
        <div className="bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs p-3 rounded-xl flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          {toastMessage}
        </div>
      )}

      {error && (
        <div className="bg-rose-950/80 border border-rose-800 text-rose-200 text-xs p-4 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <div>
            <p className="font-semibold text-rose-100">Knowledge Graph Error</p>
            <p className="text-rose-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Metric Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Graph Nodes</span>
            <Share2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {summary?.nodes_count ?? graphData.nodes.length ?? 0}
          </div>
          <div className="text-[10px] text-slate-500">PostgreSQL + NetworkX</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Relational Edges</span>
            <Network className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {summary?.edges_count ?? graphData.links.length ?? 0}
          </div>
          <div className="text-[10px] text-slate-500">Entities & Co-occurrences</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Graph Density</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {summary?.density != null ? summary.density : '0.000'}
          </div>
          <div className="text-[10px] text-slate-500">Network connection ratio</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Top Central Entity</span>
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-sm font-bold text-slate-100 truncate">
            {summary?.top_centrality_nodes?.[0]?.name || 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500">
            {summary?.top_centrality_nodes?.[0] ? `${summary.top_centrality_nodes[0].type} (${summary.top_centrality_nodes[0].degree} links)` : 'No nodes yet'}
          </div>
        </div>
      </div>

      {/* Interactive Force-Directed Graph Component */}
      <ProjectGraphViewer
        nodes={displayNodes}
        links={displayLinks}
        isLoading={loading}
        onRefresh={fetchData}
      />
    </div>
  );
};
