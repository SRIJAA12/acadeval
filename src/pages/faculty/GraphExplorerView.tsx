import React, { useEffect, useState, useCallback } from 'react';
import {
  Share2, RefreshCw, Cpu, Network, ShieldCheck, Activity, AlertCircle,
  GitCompare, Layers, Compass, ChevronLeft, ChevronRight
} from 'lucide-react';
import { ProjectGraphViewer } from '../../components/ProjectGraphViewer';
import {
  getAllProjects,
  getGraphSummary,
  getGraphVisualization,
  rebuildKnowledgeGraph,
  getProjectGraph,
  getComparisonGraph,
  rebuildProjectGraph
} from '../../api/endpoints';

type GraphTab = 'global' | 'project' | 'comparison';

export const GraphExplorerView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<GraphTab>('global');
  const [summary, setSummary] = useState<any>(null);
  const [globalGraphData, setGlobalGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [projectGraphData, setProjectGraphData] = useState<{ nodes: any[]; links: any[]; title?: string }>({ nodes: [], links: [] });
  const [comparisonTargetData, setComparisonTargetData] = useState<{ nodes: any[]; links: any[]; title?: string }>({ nodes: [], links: [] });
  const [comparisonSideData, setComparisonSideData] = useState<{ nodes: any[]; links: any[]; title?: string } | null>(null);
  const [allProjectsList, setAllProjectsList] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [comparisonProjectId, setComparisonProjectId] = useState<string>('');
  const [distanceThreshold, setDistanceThreshold] = useState<number>(0.5);
  const [loading, setLoading] = useState<boolean>(true);
  const [rebuilding, setRebuilding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [similarityScore, setSimilarityScore] = useState<number | null>(null);
  const [relatedAvailable, setRelatedAvailable] = useState<boolean | null>(null);

  const fetchGlobalData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, vizRes, projListRes] = await Promise.all([
        getGraphSummary(true).catch(e => { console.warn('getGraphSummary failed:', e); return null; }),
        getGraphVisualization(400).catch(e => { console.warn('getGraphVisualization failed:', e); return null; }),
        getAllProjects().catch(e => { console.warn('getAllProjects failed:', e); return []; }),
      ]);
      if (sumRes) setSummary(sumRes.metrics || null);
      const projects = Array.isArray(projListRes) ? projListRes : [];
      setAllProjectsList(projects);
      if (projects.length > 0 && !selectedProjectId) {
        setSelectedProjectId(projects[0].projectId);
        if (projects.length > 1) {
          setComparisonProjectId(projects[1].projectId);
        }
      }
      setGlobalGraphData({
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

  const fetchProjectGraph = useCallback(async (projectId: string) => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const pData = await getProjectGraph(projectId);
      setProjectGraphData({
        nodes: pData?.nodes || [],
        links: pData?.links || [],
        title: pData?.title,
      });
    } catch (err: any) {
      console.error('Failed to load project graph:', err);
      setError(err?.message || 'Failed to load project graph.');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchComparisonGraphs = useCallback(async (targetId: string, compId: string) => {
    if (!targetId) return;
    setLoading(true);
    setError(null);
    setSimilarityScore(null);
    setRelatedAvailable(null);
    try {
      // Always fetch both graphs independently for side-by-side display
      const targetPromise = getProjectGraph(targetId);
      const compPromise = compId && compId !== targetId ? getProjectGraph(compId) : null;

      // Also try the comparison endpoint to get similarity score
      const compEndpointPromise = getComparisonGraph(targetId, distanceThreshold).catch(() => null);

      const [targetData, compData, compEndpointData] = await Promise.all([
        targetPromise,
        compPromise,
        compEndpointPromise,
      ]);

      setComparisonTargetData({
        nodes: targetData?.nodes || [],
        links: targetData?.links || [],
        title: targetData?.title,
      });

      if (compData) {
        setComparisonSideData({
          nodes: compData?.nodes || [],
          links: compData?.links || [],
          title: compData?.title,
        });
      } else {
        setComparisonSideData(null);
      }

      // Use comparison endpoint similarity score if available
      if (compEndpointData?.related_project_available) {
        setSimilarityScore(compEndpointData.similarity_score ?? null);
        setRelatedAvailable(true);
      } else {
        setRelatedAvailable(compId && compId !== targetId ? true : false);
        setSimilarityScore(null);
      }
    } catch (err: any) {
      console.error('Failed to load comparison graphs:', err);
      setError(err?.message || 'Failed to load comparison graphs.');
    } finally {
      setLoading(false);
    }
  }, [distanceThreshold]);

  useEffect(() => {
    fetchGlobalData();
  }, []);

  useEffect(() => {
    if (activeTab === 'project' && selectedProjectId) {
      fetchProjectGraph(selectedProjectId);
    } else if (activeTab === 'comparison' && selectedProjectId) {
      fetchComparisonGraphs(selectedProjectId, comparisonProjectId);
    }
  }, [activeTab, selectedProjectId, comparisonProjectId, distanceThreshold]);

  const handleGlobalRebuild = async () => {
    if (!window.confirm('Rebuild Knowledge Graph from all project submissions in PostgreSQL?')) return;
    setRebuilding(true);
    try {
      const res = await rebuildKnowledgeGraph();
      setToastMessage(`Bulk graph rebuilt successfully: ${res?.result?.projects_processed || 0} projects, ${res?.result?.relational_nodes || 0} nodes.`);
      await fetchGlobalData();
    } catch (err: any) {
      alert('Failed to rebuild graph: ' + (err?.message || err));
    } finally {
      setRebuilding(false);
      setTimeout(() => setToastMessage(null), 5000);
    }
  };

  const handleProjectRebuild = async () => {
    if (!selectedProjectId) return;
    const target = allProjectsList.find(p => p.projectId === selectedProjectId);
    const name = target?.title || selectedProjectId;
    if (!window.confirm(`Reconstruct graph for "${name}"?`)) return;

    setRebuilding(true);
    try {
      const res = await rebuildProjectGraph(selectedProjectId);
      setToastMessage(`Project graph reconstructed: ${res?.result?.relational_nodes_ingested || 0} nodes updated.`);
      if (activeTab === 'project') {
        await fetchProjectGraph(selectedProjectId);
      } else if (activeTab === 'comparison') {
        await fetchComparisonGraphs(selectedProjectId, comparisonProjectId);
      } else {
        await fetchGlobalData();
      }
    } catch (err: any) {
      alert('Failed to reconstruct project graph: ' + (err?.message || err));
    } finally {
      setRebuilding(false);
      setTimeout(() => setToastMessage(null), 5000);
    }
  };

  const currentDisplayNodes = activeTab === 'project'
    ? projectGraphData.nodes
    : activeTab === 'global'
    ? globalGraphData.nodes
    : comparisonTargetData.nodes;

  const currentDisplayLinks = activeTab === 'project'
    ? projectGraphData.links
    : activeTab === 'global'
    ? globalGraphData.links
    : comparisonTargetData.links;

  // Compute shared entity names between two graphs for highlighting
  const sharedEntityNames = React.useMemo(() => {
    if (!comparisonSideData || !comparisonTargetData.nodes.length) return new Set<string>();
    const targetNames = new Set(
      comparisonTargetData.nodes
        .filter(n => n.type !== 'Project')
        .map(n => n.name?.toLowerCase().trim())
    );
    const shared = new Set<string>();
    comparisonSideData.nodes.forEach(n => {
      if (n.type !== 'Project' && targetNames.has(n.name?.toLowerCase().trim())) {
        shared.add(n.name?.toLowerCase().trim());
      }
    });
    return shared;
  }, [comparisonTargetData, comparisonSideData]);

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
              {activeTab === 'global' ? 'Global MultiDiGraph' : activeTab === 'project' ? 'Project Scoped Graph' : 'Dual-Project Comparison'}
            </span>
          </h1>
          <p className="text-xs text-slate-400 max-w-2xl">
            Visualise and inspect project knowledge graphs. Toggle between the global network, an isolated project's entity subgraph, or a side-by-side comparison of two projects.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {activeTab !== 'global' && (
            <div className="flex flex-col">
              <label className="text-[10px] text-slate-400 font-semibold uppercase mb-1">
                {activeTab === 'comparison' ? 'Project A (Target)' : 'Target Project'}
              </label>
              <select
                value={selectedProjectId}
                onChange={e => setSelectedProjectId(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 outline-none max-w-xs truncate"
              >
                {allProjectsList.map(p => (
                  <option key={p.projectId} value={p.projectId}>
                    📁 {p.title.length > 35 ? p.title.substring(0, 35) + '...' : p.title} ({p.studentName})
                  </option>
                ))}
              </select>
            </div>
          )}

          {activeTab === 'comparison' && (
            <div className="flex items-center gap-2 self-end">
              <ChevronLeft className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-semibold text-indigo-300">vs</span>
              <ChevronRight className="w-4 h-4 text-indigo-400" />
            </div>
          )}

          {activeTab === 'comparison' && (
            <div className="flex flex-col">
              <label className="text-[10px] text-slate-400 font-semibold uppercase mb-1">Project B (Comparison)</label>
              <select
                value={comparisonProjectId}
                onChange={e => setComparisonProjectId(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-violet-500 outline-none max-w-xs truncate"
              >
                <option value="">— None —</option>
                {allProjectsList
                  .filter(p => p.projectId !== selectedProjectId)
                  .map(p => (
                    <option key={p.projectId} value={p.projectId}>
                      📁 {p.title.length > 35 ? p.title.substring(0, 35) + '...' : p.title} ({p.studentName})
                    </option>
                  ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-2 mt-4">
            <button
              onClick={() => {
                if (activeTab === 'global') fetchGlobalData();
                else if (activeTab === 'project') fetchProjectGraph(selectedProjectId);
                else fetchComparisonGraphs(selectedProjectId, comparisonProjectId);
              }}
              disabled={loading}
              className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>

            {activeTab !== 'global' && selectedProjectId && (
              <button
                onClick={handleProjectRebuild}
                disabled={rebuilding || loading}
                title="Reconstruct only this project's graph"
                className="px-3.5 py-2 bg-teal-700 hover:bg-teal-600 text-white text-xs font-medium rounded-xl border border-teal-600 transition flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
                {rebuilding ? 'Rebuilding…' : 'Reconstruct Project'}
              </button>
            )}

            <button
              onClick={handleGlobalRebuild}
              disabled={rebuilding || loading}
              className="px-3.5 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-xs font-medium rounded-xl border border-indigo-600 transition flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
              {rebuilding ? 'Rebuilding…' : 'Rebuild All'}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('global')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'global'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Layers className="w-4 h-4" /> Global Knowledge Graph
        </button>
        <button
          onClick={() => {
            setActiveTab('project');
            if (selectedProjectId) fetchProjectGraph(selectedProjectId);
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'project'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Compass className="w-4 h-4" /> Project Graph
        </button>
        <button
          onClick={() => {
            setActiveTab('comparison');
            if (selectedProjectId) fetchComparisonGraphs(selectedProjectId, comparisonProjectId);
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'comparison'
              ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <GitCompare className="w-4 h-4" /> Side-by-Side Comparison
        </button>
      </div>

      {/* Comparison Status Banner */}
      {activeTab === 'comparison' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="bg-indigo-950/60 border border-indigo-800 text-indigo-200 text-xs p-3 rounded-xl flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-indigo-400 flex-shrink-0" />
            <div>
              <p className="font-semibold text-indigo-100">{comparisonTargetData.title || allProjectsList.find(p => p.projectId === selectedProjectId)?.title || 'Project A'}</p>
              <p className="text-indigo-400">{comparisonTargetData.nodes.length} nodes · {comparisonTargetData.links.length} edges</p>
            </div>
          </div>
          <div className="flex items-center justify-center">
            {similarityScore !== null ? (
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-400">{(similarityScore * 100).toFixed(1)}%</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Similarity Score</div>
              </div>
            ) : sharedEntityNames.size > 0 ? (
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-400">{sharedEntityNames.size}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Shared Entities</div>
              </div>
            ) : (
              <div className="text-center">
                <GitCompare className="w-6 h-6 text-slate-600 mx-auto" />
                <div className="text-[10px] text-slate-500 mt-1">Select two projects</div>
              </div>
            )}
          </div>
          <div className={`${comparisonSideData ? 'bg-violet-950/60 border-violet-800' : 'bg-slate-900/60 border-slate-700'} border text-xs p-3 rounded-xl flex items-center gap-3`}>
            {comparisonSideData ? (
              <>
                <div className="w-2 h-2 rounded-full bg-violet-400 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-violet-100">{comparisonSideData.title || allProjectsList.find(p => p.projectId === comparisonProjectId)?.title || 'Project B'}</p>
                  <p className="text-violet-400">{comparisonSideData.nodes.length} nodes · {comparisonSideData.links.length} edges</p>
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0" />
                <p className="text-slate-500">Select Project B from the dropdown above</p>
              </>
            )}
          </div>
        </div>
      )}

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
            {activeTab === 'global' ? (summary?.nodes_count ?? currentDisplayNodes.length) : currentDisplayNodes.length}
          </div>
          <div className="text-[10px] text-slate-500">PostgreSQL + NetworkX</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Relational Edges</span>
            <Network className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {activeTab === 'global' ? (summary?.edges_count ?? currentDisplayLinks.length) : currentDisplayLinks.length}
          </div>
          <div className="text-[10px] text-slate-500">Entities &amp; Co-occurrences</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>{activeTab === 'comparison' ? 'Shared Entities' : 'Graph Density'}</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {activeTab === 'comparison'
              ? sharedEntityNames.size
              : (summary?.density != null ? summary.density : '0.000')}
          </div>
          <div className="text-[10px] text-slate-500">
            {activeTab === 'comparison' ? 'Common techniques/tech' : 'Network connection ratio'}
          </div>
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

      {/* Graph Display */}
      {activeTab === 'comparison' ? (
        /* Dual Panel Comparison Layout */
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Panel A — Target Project */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 flex-shrink-0" />
              <span className="text-sm font-semibold text-indigo-300">
                {comparisonTargetData.title || allProjectsList.find(p => p.projectId === selectedProjectId)?.title || 'Project A'}
              </span>
              <span className="ml-auto text-[10px] font-mono text-slate-500">
                {comparisonTargetData.nodes.length}N · {comparisonTargetData.links.length}E
              </span>
            </div>
            <ProjectGraphViewer
              nodes={comparisonTargetData.nodes}
              links={comparisonTargetData.links}
              isLoading={loading && comparisonTargetData.nodes.length === 0}
              highlightNames={sharedEntityNames}
              accentColor="#6366f1"
              onRefresh={() => fetchComparisonGraphs(selectedProjectId, comparisonProjectId)}
            />
          </div>

          {/* Panel B — Comparison Project */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <div className="w-2.5 h-2.5 rounded-full bg-violet-500 flex-shrink-0" />
              <span className="text-sm font-semibold text-violet-300">
                {comparisonSideData?.title || allProjectsList.find(p => p.projectId === comparisonProjectId)?.title || 'Project B'}
              </span>
              {comparisonSideData && (
                <span className="ml-auto text-[10px] font-mono text-slate-500">
                  {comparisonSideData.nodes.length}N · {comparisonSideData.links.length}E
                </span>
              )}
            </div>
            {comparisonSideData ? (
              <ProjectGraphViewer
                nodes={comparisonSideData.nodes}
                links={comparisonSideData.links}
                isLoading={loading && comparisonSideData.nodes.length === 0}
                highlightNames={sharedEntityNames}
                accentColor="#8b5cf6"
                onRefresh={() => fetchComparisonGraphs(selectedProjectId, comparisonProjectId)}
              />
            ) : (
              <div className="h-[760px] bg-slate-900 border border-slate-800 rounded-2xl flex flex-col items-center justify-center gap-4 text-slate-500">
                <GitCompare className="w-12 h-12 text-slate-700" />
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-400">No comparison project selected</p>
                  <p className="text-xs mt-1">Select Project B from the dropdown above to compare side by side</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Single Graph View */
        <ProjectGraphViewer
          nodes={currentDisplayNodes}
          links={currentDisplayLinks}
          isLoading={loading}
          onRefresh={() => {
            if (activeTab === 'global') fetchGlobalData();
            else fetchProjectGraph(selectedProjectId);
          }}
        />
      )}
    </div>
  );
};
