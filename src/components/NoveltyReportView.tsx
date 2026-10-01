import React, { useMemo, useState, useEffect } from 'react';
import {
  Sparkles, Network, TrendingUp, CheckCircle, Layers,
  Cpu, Database, Grid, Info, ChevronDown, ChevronUp, Share2, HelpCircle,
  ArrowRightLeft, GitCompare, GitFork, ExternalLink, ShieldCheck
} from 'lucide-react';
import { ProjectGraphViewer, type GraphNodeData, type GraphLinkData } from './ProjectGraphViewer';
import { getProjectGraph, getComparisonGraph } from '../api/endpoints';

export interface SignalBreakdown {
  graph_distance: number;
  feature_rarity: number;
  relationship_rarity: number;
  graph_density: number;
  new_connection_discovery: number;
}

export interface ExtractedEntities {
  algorithms: string[];
  technologies: string[];
  frameworks: string[];
  libraries: string[];
  datasets: string[];
  applications: string[];
  hardware: string[];
  metrics?: string[];
}

export interface TrendContext {
  topic: string;
  growth_rate_pct: number | null;
  paper_count_3yr: number | null;
  citation_velocity: number | null;
  trend_status: string;
  data_source?: string;
}

export interface SimilarProject {
  project_id: string;
  title: string;
  similarity_score: number;
}

export interface ScoringMetadata {
  method_version: string;
  combiner: string;
  corpus_snapshot_id: string;
  corpus_project_count: number;
  snapshot_captured_at: string;
  top_k: number;
  evidence_quality: 'empty' | 'limited' | 'adequate';
  candidate_preexisting_in_graph: boolean;
  candidate_excluded_from_snapshot: boolean;
}

export interface NoveltyReportData {
  project_id: string;
  title: string;
  domain: string;
  sub_domain: string;
  overall_novelty_band: string;
  overall_novelty_score: number;
  signals_breakdown: SignalBreakdown;
  extracted_entities: ExtractedEntities;
  trend_context: TrendContext;
  most_similar_projects: SimilarProject[];
  explanation_lines: string[];
  scoring_metadata?: ScoringMetadata;
}

export interface ComparisonGraphPayload {
  status: string;
  project_id: string;
  target_title: string;
  comparison_title: string;
  comparison_project_id?: string;
  comparison_domain?: string;
  comparison_sub_domain?: string;
  related_project_available: boolean;
  similarity_score: number;
  distance?: number;
  shared_entities_count?: number;
  shared_entities?: string[];
  message: string;
  similar_projects: Array<{
    project_id: string;
    title: string;
    similarity_score: number;
    distance?: number;
    domain?: string;
    sub_domain?: string;
    shared_entities?: string[];
  }>;
  nodes: GraphNodeData[];
  links: GraphLinkData[];
  target_graph?: { nodes: GraphNodeData[]; links: GraphLinkData[]; title?: string };
  comparison_graph?: { nodes: GraphNodeData[]; links: GraphLinkData[]; title?: string };
}

interface Props {
  report: NoveltyReportData;
  onFacultyScoreSubmit?: (facultyScore: number, reason: string) => void;
  /** Real DB-extracted entities to use in fallback subgraph builder */
  realEntities?: {
    algorithms?: string[];
    technologies?: string[];
    frameworks?: string[];
    libraries?: string[];
    datasets?: string[];
    applications?: string[];
    hardware?: string[];
    metrics?: string[];
  } | null;
}

export const NoveltyReportView: React.FC<Props> = ({ report, onFacultyScoreSubmit, realEntities }) => {
  const [facultyRating, setFacultyRating] = useState<number>(8);
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [submitted, setSubmitted] = useState<boolean>(false);
  const [showDocExplain, setShowDocExplain] = useState<boolean>(true);

  const getBandColor = (band: string) => {
    if (band.includes('Insufficient')) return 'bg-slate-950 text-slate-300 border-slate-700';
    if (band.includes('Moderately')) return 'bg-amber-950 text-amber-300 border-amber-800';
    if (band.includes('Highly')) return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    return 'bg-blue-950 text-blue-300 border-blue-800';
  };

  const handleFacultySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onFacultyScoreSubmit) {
      onFacultyScoreSubmit(facultyRating, overrideReason);
      setSubmitted(true);
    }
  };

  // Fetch project-scoped graph and comparison graph directly from the backend
  const [fullGraph, setFullGraph] = useState<{ nodes: GraphNodeData[]; links: GraphLinkData[] }>({ nodes: [], links: [] });
  const [graphLoading, setGraphLoading] = useState(false);
  const [compLoading, setCompLoading] = useState(false);
  const [comparisonPayload, setComparisonPayload] = useState<ComparisonGraphPayload | null>(null);
  const [graphViewMode, setGraphViewMode] = useState<'dual' | 'unified' | 'uploaded'>('dual');
  const [selectedCompProjectId, setSelectedCompProjectId] = useState<string>('');

  const fetchComparison = (targetId: string, candidateId?: string) => {
    setCompLoading(true);
    getComparisonGraph(targetId, candidateId)
      .then(res => {
        if (res && res.status === 'ok') {
          setComparisonPayload(res);
          if (res.comparison_project_id) {
            setSelectedCompProjectId(res.comparison_project_id);
          }
        }
      })
      .catch(err => {
        console.warn('Failed to fetch comparison graph:', err);
      })
      .finally(() => setCompLoading(false));
  };

  useEffect(() => {
    if (!report?.project_id) return;
    setGraphLoading(true);

    getProjectGraph(report.project_id)
      .then(res => {
        if (res && res.nodes && res.links) {
          setFullGraph({ nodes: res.nodes, links: res.links });
        }
      })
      .catch(err => {
        console.warn('Failed to fetch project graph, falling back to local build:', err);
      })
      .finally(() => setGraphLoading(false));

    fetchComparison(report.project_id);
  }, [report?.project_id]);

  const handleComparisonProjectChange = (candidateId: string) => {
    setSelectedCompProjectId(candidateId);
    if (report?.project_id) {
      fetchComparison(report.project_id, candidateId);
    }
  };

  // If backend graph loaded successfully, use it directly.
  // Otherwise fall back to local entity-based subgraph builder.
  const { nodes: subNodes, links: subLinks } = useMemo(() => {
    if (!report) return { nodes: [], links: [] };

    // Backend graph available — use it directly
    if (fullGraph.nodes.length > 0) {
      return { nodes: fullGraph.nodes, links: fullGraph.links };
    }

    // Fallback: local graph generation using real DB entities if available
    const nodeList: GraphNodeData[] = [];
    const linkList: GraphLinkData[] = [];
    let nextId = 1;

    // Prefer realEntities (from DB) over report.extracted_entities (from novelty API)
    const entities = {
      algorithms: (realEntities?.algorithms?.length ? realEntities.algorithms : report.extracted_entities?.algorithms) || [],
      technologies: (realEntities?.technologies?.length ? realEntities.technologies : report.extracted_entities?.technologies) || [],
      frameworks: (realEntities?.frameworks?.length ? realEntities.frameworks : report.extracted_entities?.frameworks) || [],
      libraries: (realEntities?.libraries?.length ? realEntities.libraries : report.extracted_entities?.libraries) || [],
      datasets: (realEntities?.datasets?.length ? realEntities.datasets : report.extracted_entities?.datasets) || [],
      applications: (realEntities?.applications?.length ? realEntities.applications : report.extracted_entities?.applications) || [],
      hardware: (realEntities?.hardware?.length ? realEntities.hardware : report.extracted_entities?.hardware) || [],
      metrics: (realEntities?.metrics?.length ? realEntities.metrics : report.extracted_entities?.metrics) || [],
    };

    // 1. Central Project Node
    const projId = nextId++;
    nodeList.push({
      id: projId,
      name: report.title || 'Project Submission',
      type: 'Project',
      degree: 10,
    });

    // 2. Domain & Subdomain Nodes
    if (report.domain) {
      const domId = nextId++;
      nodeList.push({ id: domId, name: report.domain, type: 'Domain', degree: 4 });
      linkList.push({ source: projId, target: domId, relationship: 'HAS_DOMAIN', confidence: 1.0 });

      if (report.sub_domain) {
        const subdomId = nextId++;
        nodeList.push({ id: subdomId, name: report.sub_domain, type: 'Subdomain', degree: 3 });
        linkList.push({ source: projId, target: subdomId, relationship: 'HAS_SUBDOMAIN', confidence: 1.0 });
        linkList.push({ source: subdomId, target: domId, relationship: 'SUBDOMAIN_OF', confidence: 1.0 });
      }
    }

    // 3. Extracted Entity Nodes
    const catMap: { list: string[]; label: string; rel: string }[] = [
      { list: entities.algorithms || [], label: 'Algorithm', rel: 'USES_ALGORITHM' },
      { list: entities.technologies || [], label: 'Technology', rel: 'USES_TECHNOLOGY' },
      { list: entities.frameworks || [], label: 'Framework', rel: 'USES_FRAMEWORK' },
      { list: entities.libraries || [], label: 'Library', rel: 'USES_LIBRARY' },
      { list: entities.datasets || [], label: 'Dataset', rel: 'USES_DATASET' },
      { list: entities.applications || [], label: 'Application', rel: 'TARGETS_APPLICATION' },
      { list: entities.hardware || [], label: 'Hardware', rel: 'RUNS_ON' },
      { list: entities.metrics || [], label: 'Metric', rel: 'EVALUATED_BY' },
    ];

    const entityNodeIds: number[] = [];

    catMap.forEach(({ list, label, rel }) => {
      list.forEach(name => {
        if (!name) return;
        const entId = nextId++;
        nodeList.push({ id: entId, name, type: label, degree: 3 });
        linkList.push({ source: projId, target: entId, relationship: rel, confidence: 1.0 });
        entityNodeIds.push(entId);
      });
    });

    // 4. Similar Project Nodes (no CO_OCCURS — they create N² explosion)
    (report.most_similar_projects || []).slice(0, 3).forEach((simProj) => {
      const simId = nextId++;
      nodeList.push({ id: simId, name: simProj.title, type: 'Project', degree: 4 });
      linkList.push({
        source: projId,
        target: simId,
        relationship: 'SIMILAR_TO',
        confidence: simProj.similarity_score,
      });
    });

    return { nodes: nodeList, links: linkList };
  }, [report, fullGraph, realEntities]);

  // Resolved Target Graph (Graph 1: Current Uploaded Project)
  const targetGraphNodes = useMemo(() => {
    if (comparisonPayload?.target_graph?.nodes && comparisonPayload.target_graph.nodes.length > 0) {
      return comparisonPayload.target_graph.nodes;
    }
    return subNodes;
  }, [comparisonPayload, subNodes]);

  const targetGraphLinks = useMemo(() => {
    if (comparisonPayload?.target_graph?.links && comparisonPayload.target_graph.links.length > 0) {
      return comparisonPayload.target_graph.links;
    }
    return subLinks;
  }, [comparisonPayload, subLinks]);

  // Comparison Reference Title
  const comparisonTitle = useMemo(() => {
    if (comparisonPayload?.comparison_title) return comparisonPayload.comparison_title;
    return 'Related Research Project from Dataset Corpus';
  }, [comparisonPayload]);

  const isRelatedAvailable = useMemo(() => {
    if (!comparisonPayload) return true; // loading or initial
    return comparisonPayload.related_project_available !== false && (comparisonPayload.comparison_graph?.nodes?.length ?? 0) > 0;
  }, [comparisonPayload]);

  // Resolved Comparison Graph (Graph 2: Real matched research project from AcadEval Corpus dataset)
  const { compGraphNodes, compGraphLinks } = useMemo(() => {
    if (comparisonPayload?.comparison_graph?.nodes && comparisonPayload.comparison_graph.nodes.length > 0) {
      return {
        compGraphNodes: comparisonPayload.comparison_graph.nodes,
        compGraphLinks: comparisonPayload.comparison_graph.links,
      };
    }
    return { compGraphNodes: [], compGraphLinks: [] };
  }, [comparisonPayload]);

  const similarProjects = useMemo(() => {
    return comparisonPayload?.similar_projects || [];
  }, [comparisonPayload]);

  // Unified Merged Graph (Target + Comparison + Cross-Graph Bridge)
  const { unifiedNodes, unifiedLinks } = useMemo(() => {
    if (comparisonPayload?.nodes && comparisonPayload.nodes.length > 0) {
      return {
        unifiedNodes: comparisonPayload.nodes,
        unifiedLinks: comparisonPayload.links,
      };
    }

    const uNodes = [...targetGraphNodes, ...compGraphNodes];
    const uLinks = [...targetGraphLinks, ...compGraphLinks];
    return { unifiedNodes: uNodes, unifiedLinks: uLinks };
  }, [comparisonPayload, targetGraphNodes, targetGraphLinks, compGraphNodes, compGraphLinks]);

  // Shared entity names (for golden glow highlight)
  const sharedEntityNames = useMemo(() => {
    const set = new Set<string>();
    if (comparisonPayload?.shared_entities && comparisonPayload.shared_entities.length > 0) {
      comparisonPayload.shared_entities.forEach(name => set.add(name.toLowerCase()));
    } else if (comparisonPayload?.nodes) {
      comparisonPayload.nodes.forEach(n => {
        if ((n as any).is_shared || (n as any).group === 'shared') {
          set.add(n.name.toLowerCase());
        }
      });
    }
    return set;
  }, [comparisonPayload]);

  const similarityPercentage = useMemo(() => {
    if (!isRelatedAvailable) return 0;
    const raw = comparisonPayload?.similarity_score ?? report.most_similar_projects?.[0]?.similarity_score ?? 0;
    return Math.round(raw * 100);
  }, [comparisonPayload, report, isRelatedAvailable]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto p-2">
      {/* Header Banner */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 text-indigo-400 font-mono text-xs uppercase tracking-wider mb-1">
            <Network className="w-4 h-4" /> Module 4 — Project Knowledge Graph Construction & Novelty Engine
          </div>
          <h2 className="text-2xl font-bold leading-tight">{report.title}</h2>
          <p className="text-slate-400 text-xs mt-1.5 flex items-center gap-2">
            Domain: <span className="text-slate-200 font-medium">{report.domain}</span>
            <span>&rarr;</span>
            Subdomain: <span className="text-indigo-300 font-medium">{report.sub_domain}</span>
          </p>
        </div>

        <div className="flex items-center gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800 shrink-0">
          <div className="text-center">
            <div className="text-3xl font-extrabold text-indigo-400 font-mono">{report.overall_novelty_score}</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-widest mt-0.5 font-semibold">Novelty Score</div>
          </div>
          <div className="h-10 w-px bg-slate-800" />
          <span className={`px-3 py-1.5 text-xs font-semibold rounded-full border ${getBandColor(report.overall_novelty_band)}`}>
            {report.overall_novelty_band}
          </span>
        </div>
      </div>

      {/* SECTION 1: Dual-Graph Architecture: Current vs. Benchmark Corpus Projects */}
      <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-5">
        {/* Header and View Mode Switcher */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-indigo-400" />
              <h3 className="text-lg font-bold text-slate-100">
                Graph Architecture: Current Implementation vs. Corpus Baseline
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Dual-graph structural comparison: inspect the uploaded implementation alongside similar research projects from the 4,191+ AcadEval dataset corpus.
            </p>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 shrink-0">
            <button
              onClick={() => setGraphViewMode('dual')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                graphViewMode === 'dual'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ArrowRightLeft className="w-3.5 h-3.5" /> Dual Comparison
            </button>
            <button
              onClick={() => setGraphViewMode('unified')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                graphViewMode === 'unified'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitFork className="w-3.5 h-3.5" /> Unified Overlay
            </button>
            <button
              onClick={() => setGraphViewMode('uploaded')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                graphViewMode === 'uploaded'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Share2 className="w-3.5 h-3.5" /> Current Only
            </button>
          </div>
        </div>

        {/* Central Explicit Relationship Bridge Banner */}
        <div className="bg-slate-950/90 p-4 rounded-xl border border-indigo-900/60 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-950 flex items-center justify-center border border-indigo-700 text-indigo-400 shrink-0">
              <ArrowRightLeft className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-wider bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800">
                  Explicit Relationship: BENCHMARKED_AGAINST
                </span>
                {isRelatedAvailable && (
                  <span className="text-[10px] font-mono uppercase tracking-wider bg-amber-950 text-amber-300 px-2 py-0.5 rounded border border-amber-800">
                    CORPUS_MATCH (Distance &le; 0.50)
                  </span>
                )}
                {!isRelatedAvailable && (
                  <span className="text-[10px] font-mono uppercase tracking-wider bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded border border-emerald-800">
                    NOVEL (Distance &gt; 0.50)
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-300 mt-1">
                {isRelatedAvailable ? (
                  <>
                    Comparing <strong className="text-white">{report.title}</strong> against dataset project{' '}
                    <strong className="text-amber-300">{comparisonPayload?.comparison_title || 'Corpus Baseline'}</strong>
                    {comparisonPayload?.comparison_domain && (
                      <span className="text-slate-400"> ({comparisonPayload.comparison_domain})</span>
                    )}
                  </>
                ) : (
                  <>
                    <strong className="text-white">{report.title}</strong> has no close duplicate in the dataset corpus (Distance &gt; 0.50).
                  </>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <div className="text-xs text-slate-400">Corpus Similarity</div>
              <div className="text-xl font-bold font-mono text-amber-400">
                {isRelatedAvailable ? `${similarityPercentage}%` : 'N/A'}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div className="text-right">
              <div className="text-xs text-slate-400">Shared Entities</div>
              <div className="text-xl font-bold font-mono text-emerald-400">{sharedEntityNames.size}</div>
            </div>
          </div>
        </div>

        {/* Shared Overlap Entities Banner */}
        {sharedEntityNames.size > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs bg-slate-950/50 p-3 rounded-xl border border-slate-800/80">
            <span className="text-slate-400 font-semibold flex items-center gap-1 shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Shared Overlap with Corpus Match (Golden Glow in Graph):
            </span>
            {Array.from(sharedEntityNames).slice(0, 10).map(name => (
              <span key={name} className="px-2 py-0.5 bg-amber-950/60 text-amber-200 border border-amber-800/70 rounded-md font-mono text-[11px]">
                {name}
              </span>
            ))}
            {sharedEntityNames.size > 10 && (
              <span className="text-slate-500 text-[11px]">+{sharedEntityNames.size - 10} more</span>
            )}
          </div>
        )}

        {/* Dynamic Graph Views based on mode */}
        {graphViewMode === 'dual' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Graph 1: Current Uploaded Project */}
            <div className="space-y-2">
              <div className="flex items-center justify-between bg-slate-950/80 px-3 py-2 rounded-xl border border-slate-800">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 shrink-0" />
                  <span className="text-xs font-bold text-slate-200 truncate">
                    Graph 1: Current Implementation ({report.title})
                  </span>
                </div>
                <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950/80 border border-indigo-800/80 px-2 py-0.5 rounded shrink-0">
                  {targetGraphNodes.length} Nodes · {targetGraphLinks.length} Edges
                </span>
              </div>
              <ProjectGraphViewer
                nodes={targetGraphNodes}
                links={targetGraphLinks}
                isLoading={graphLoading}
                height="h-[540px]"
                compact={true}
                accentColor="#6366f1"
                highlightNames={sharedEntityNames}
              />
            </div>

            {/* Graph 2: Corpus Dataset Project Header & Visualizer */}
            <div className="space-y-2">
              <div className="flex items-center justify-between bg-slate-950/80 px-3 py-2 rounded-xl border border-slate-800 gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                  <span className="text-xs font-bold text-slate-100 shrink-0">
                    Graph 2:
                  </span>
                  {isRelatedAvailable && similarProjects.length > 0 ? (
                    <select
                      value={selectedCompProjectId || comparisonPayload?.comparison_project_id || ''}
                      onChange={(e) => handleComparisonProjectChange(e.target.value)}
                      className="bg-slate-900 text-amber-300 font-bold text-xs px-2.5 py-1 rounded-lg border border-amber-800/80 focus:outline-none focus:border-amber-400 cursor-pointer min-w-0 max-w-[280px] truncate"
                      title="Select any related research project from the dataset corpus to compare in Graph 2"
                    >
                      {similarProjects.map((p) => (
                        <option key={p.project_id} value={p.project_id} className="bg-slate-950 text-slate-200 font-medium">
                          {p.title} ({Math.round((p.similarity_score || 0) * 100)}% Match)
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-xs text-amber-300 font-medium truncate">
                      {comparisonTitle}
                    </span>
                  )}
                </div>
                <span className="text-[10px] font-mono text-amber-400 bg-amber-950/80 border border-amber-800/80 px-2 py-0.5 rounded shrink-0">
                  {compGraphNodes.length} Nodes · {compGraphLinks.length} Edges
                </span>
              </div>

              {isRelatedAvailable ? (
                <ProjectGraphViewer
                  nodes={compGraphNodes}
                  links={compGraphLinks}
                  isLoading={compLoading}
                  height="h-[540px]"
                  compact={true}
                  accentColor="#f59e0b"
                  highlightNames={sharedEntityNames}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-[540px] bg-slate-950/80 rounded-xl border border-slate-800 p-8 text-center space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-emerald-950/60 border border-emerald-800/80 flex items-center justify-center text-emerald-400">
                    <ShieldCheck className="w-8 h-8" />
                  </div>
                  <div className="space-y-1.5 max-w-md">
                    <div className="text-base font-bold text-slate-100">Related Project is Not Available</div>
                    <div className="text-xs font-mono text-amber-400 bg-amber-950/80 border border-amber-800/60 px-2.5 py-1 rounded-full inline-block">
                      Distance &gt; 0.50 (Distinct Architecture)
                    </div>
                    <p className="text-xs text-slate-400 mt-2">
                      No candidate research project in the 4,191+ AcadEval Corpus Dataset exceeded the 50% similarity threshold.
                      This submission represents a distinct architectural configuration with no close duplicates.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Dataset Corpus Match Candidates Matrix */}
        <div className="p-4 bg-slate-950/90 rounded-xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-amber-400" /> AcadEval Research Corpus Ground Truth (4,191+ Indexed Projects in <code className="text-indigo-300 font-mono">AcadEval_Corpus_MASTER.csv</code>)
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {similarProjects.length > 0 ? 'Click any matched project to view in Graph 2' : 'Distance > 0.50'}
            </span>
          </div>

          {similarProjects.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
              {similarProjects.slice(0, 6).map((proj) => {
                const isSelected = (selectedCompProjectId || comparisonPayload?.comparison_project_id) === proj.project_id;
                return (
                  <div
                    key={proj.project_id}
                    onClick={() => handleComparisonProjectChange(proj.project_id)}
                    className={`p-3 rounded-lg border flex flex-col justify-between cursor-pointer transition ${
                      isSelected
                        ? 'bg-amber-950/50 border-amber-500 ring-1 ring-amber-500/50'
                        : 'bg-slate-900/90 border-slate-800 hover:border-amber-700/60'
                    }`}
                    title={`Click to switch Graph 2 to ${proj.title}`}
                  >
                    <div>
                      <div className="font-semibold text-slate-200 text-xs leading-tight flex items-center justify-between gap-2">
                        <span className="truncate">{proj.title}</span>
                        {isSelected && (
                          <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" title="Active in Graph 2" />
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1.5">
                        <span className="text-slate-300">{proj.domain || 'CSE'}</span>
                        {proj.sub_domain && <span>&rarr; {proj.sub_domain}</span>}
                      </div>
                    </div>
                    <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                      <span className="font-mono text-amber-300 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-900/50">
                        {Math.round((proj.similarity_score || 0) * 100)}% Similarity
                      </span>
                      <span className="font-mono text-slate-400">
                        Dist: {proj.distance !== undefined ? proj.distance : (1 - (proj.similarity_score || 0)).toFixed(2)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800 text-center text-xs text-slate-400">
              No dataset projects in <code className="text-indigo-300 font-mono">AcadEval_Corpus_MASTER.csv</code> met the &le; 0.50 distance threshold for this submission.
            </div>
          )}
        </div>

        {graphViewMode === 'unified' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between bg-slate-950/80 px-3 py-2 rounded-xl border border-slate-800">
              <span className="text-xs font-bold text-slate-200">
                Unified Overlaid Knowledge Graph (Target + Comparison + BENCHMARKED_AGAINST Bridge)
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 border border-emerald-800/80 px-2 py-0.5 rounded">
                {unifiedNodes.length} Nodes · {unifiedLinks.length} Edges
              </span>
            </div>
            <ProjectGraphViewer
              nodes={unifiedNodes}
              links={unifiedLinks}
              isLoading={compLoading || graphLoading}
              height="h-[680px]"
              highlightNames={sharedEntityNames}
            />
          </div>
        )}

        {graphViewMode === 'uploaded' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between bg-slate-950/80 px-3 py-2 rounded-xl border border-slate-800">
              <span className="text-xs font-bold text-slate-200">
                Uploaded Project Subgraph ({report.title})
              </span>
              <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950/80 border border-indigo-800/80 px-2 py-0.5 rounded">
                {targetGraphNodes.length} Nodes · {targetGraphLinks.length} Edges
              </span>
            </div>
            <ProjectGraphViewer
              nodes={targetGraphNodes}
              links={targetGraphLinks}
              isLoading={graphLoading}
              height="h-[680px]"
            />
          </div>
        )}
      </div>

      {/* Versioned historical evidence */}
      <div className="bg-indigo-950/60 p-6 rounded-2xl border border-indigo-800 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-indigo-200 flex items-center gap-2">
          <Database className="w-5 h-5 text-gold-400" /> Historical Evidence Used
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 bg-slate-900/90 rounded-xl border border-emerald-800/80 space-y-2">
            <h4 className="font-bold text-emerald-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-400" /> Frozen Corpus Snapshot
            </h4>
            <p className="text-slate-200">
              <strong>{report.scoring_metadata?.corpus_project_count ?? 0}</strong> historical projects · evidence quality{' '}
              <strong className="capitalize">{report.scoring_metadata?.evidence_quality ?? 'unknown'}</strong>
            </p>
            <p className="font-mono text-[10px] text-slate-400 break-all">
              Snapshot: {report.scoring_metadata?.corpus_snapshot_id ?? 'Legacy report without snapshot metadata'}
            </p>
            <p className="text-slate-400">
              Candidate excluded: {report.scoring_metadata?.candidate_excluded_from_snapshot ? 'Yes' : 'Unknown'}
            </p>
          </div>
          <div className="p-4 bg-slate-900/90 rounded-xl border border-amber-800/80 space-y-2">
            <h4 className="font-bold text-amber-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-amber-400" /> Nearest Historical Match
            </h4>
            {report.most_similar_projects?.[0] ? (
              <>
                <p className="text-slate-200 font-semibold">{report.most_similar_projects[0].title}</p>
                <p className="text-slate-400">
                  Entity-set similarity: <strong className="text-amber-200">{(report.most_similar_projects[0].similarity_score * 100).toFixed(1)}%</strong>
                </p>
              </>
            ) : (
              <p className="text-slate-400">No historical comparison is available yet.</p>
            )}
            <p className="font-mono text-[10px] text-slate-500">
              {report.scoring_metadata?.method_version ?? 'legacy-method'} · {report.scoring_metadata?.combiner ?? 'unknown-combiner'}
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 2: 5 Explainable Graph Novelty Signals */}
      <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" /> 5 Explainable Graph Novelty Signals
          </h3>
          <span className="text-xs text-slate-400">
            Click on the <strong>AI Explainability</strong> tab above for step-by-step mathematical derivations
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {[
            {
              num: 1,
              title: 'Idea Uniqueness',
              tech: 'Graph Distance',
              question: 'Is this a duplicate idea?',
              score: report.signals_breakdown.graph_distance,
              icon: Network,
              color: 'bg-indigo-500',
              desc: 'Checks if past students already built a nearly identical system.',
            },
            {
              num: 2,
              title: 'Tool & Tech Rarity',
              tech: 'Feature Rarity',
              question: 'Are tools rare or standard?',
              score: report.signals_breakdown.feature_rarity,
              icon: Cpu,
              color: 'bg-emerald-500',
              desc: 'Checks if libraries & models are cutting-edge vs classroom defaults.',
            },
            {
              num: 3,
              title: 'Novel Combos',
              tech: 'Relationship Rarity',
              question: 'Unconventional pairing?',
              score: report.signals_breakdown.relationship_rarity,
              icon: Layers,
              color: 'bg-amber-500',
              desc: 'Evaluates if known tools are paired in unexpected, creative ways.',
            },
            {
              num: 4,
              title: 'Unexplored Area',
              tech: 'Graph Density',
              question: 'Overcrowded topic?',
              score: report.signals_breakdown.graph_density,
              icon: Grid,
              color: 'bg-cyan-500',
              desc: 'Checks if the sub-domain is saturated or greenfield research.',
            },
            {
              num: 5,
              title: 'Cross-Field Bridge',
              tech: 'Adamic-Adar Discovery',
              question: 'Interdisciplinary link?',
              score: report.signals_breakdown.new_connection_discovery,
              icon: Sparkles,
              color: 'bg-purple-500',
              desc: 'Tests if this proposal bridges two previously isolated fields.',
            },
          ].map((signal, idx) => (
            <div key={idx} className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-2.5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
                  <span className="text-indigo-400 font-bold">Signal {signal.num}</span>
                  <signal.icon className="w-4 h-4 text-slate-400" />
                </div>
                <h4 className="font-bold text-slate-100 text-sm mt-0.5">{signal.title}</h4>
                <div className="text-[10px] text-slate-500 font-mono">({signal.tech})</div>
                <div className="mt-1 text-[11px] text-indigo-300 font-medium italic">
                  &ldquo;{signal.question}&rdquo;
                </div>
              </div>

              <div>
                <div className="text-2xl font-bold text-slate-100 font-mono">{(signal.score * 100).toFixed(1)}%</div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className={`h-full ${signal.color}`} style={{ width: `${Math.min(100, signal.score * 100)}%` }} />
                </div>
                <p className="text-[11px] text-slate-400 leading-tight pt-2 mt-1 border-t border-slate-900">{signal.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Plain Language Explanations */}
        <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-indigo-400" /> System Explanations & Signals Details
          </h4>
          <ul className="space-y-2 text-xs text-slate-300">
            {report.explanation_lines.map((line, idx) => (
              <li key={idx} className="flex items-start gap-2 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                <span className="text-indigo-400 font-bold mt-0.5 shrink-0">•</span>
                <span className="leading-relaxed">{line}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* SECTION 3: Educational Methodology Guide — Why Graphs Uncover Hidden Similarity */}
      <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <button
          onClick={() => setShowDocExplain(!showDocExplain)}
          className="w-full flex items-center justify-between text-left focus:outline-none"
        >
          <div className="flex items-center gap-2.5">
            <HelpCircle className="w-5 h-5 text-indigo-400" />
            <div>
              <h3 className="text-base font-bold text-slate-100">How Graphs Reveal Similarity That Text Hides</h3>
              <p className="text-xs text-slate-400">Why AcadEval+ relies on graph representation over plain-text keyword matching</p>
            </div>
          </div>
          {showDocExplain ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </button>

        {showDocExplain && (
          <div className="space-y-4 pt-3 border-t border-slate-800 text-xs text-slate-300 leading-relaxed">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <h4 className="font-bold text-slate-200 text-xs flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500" /> Plain-Text Comparison Limitations
                </h4>
                <p className="text-slate-400">
                  Two student proposals with completely different wording (e.g. <i>"Deep Learning Attendance System"</i> vs <i>"Vision-based Student Presence Monitoring"</i>) appear distinct to standard keyword algorithms.
                </p>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <h4 className="font-bold text-slate-200 text-xs flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" /> Knowledge Graph Structural Resolution
                </h4>
                <p className="text-slate-400">
                  AcadEval+ resolves both proposals to the exact same canonical node path: <span className="font-mono text-indigo-300">Attendance &rarr; Computer Vision &rarr; Face Recognition</span>. Comparing structural graphs catches deep methodology overlap that text hides.
                </p>
              </div>
            </div>

            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 flex items-start gap-3">
              <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-slate-200 text-xs mb-1">Shared Entity Deduplication (`MERGE` Cypher Logic):</p>
                <p className="text-slate-400">
                  If 50 existing projects use <span className="font-mono text-slate-200">"CNN"</span>, the system reuses the same <span className="font-mono text-cyan-300">Algorithm("CNN")</span> node instead of creating 50 duplicate nodes. This shared-node structure is precisely what allows rarity, density, and new-connection signals to be computed accurately.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 4: Extracted Entities & Literature Trend Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Extracted Entities List */}
        <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-3">
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-400" /> Extracted Node Vocabulary
          </h3>
          <div className="space-y-2.5 text-xs">
            {report.extracted_entities.algorithms?.length > 0 && (
              <div>
                <span className="font-semibold text-slate-400 block mb-1">Algorithms:</span>
                {report.extracted_entities.algorithms.map((a, i) => (
                  <span key={i} className="inline-block bg-cyan-950 text-cyan-200 border border-cyan-800 px-2 py-0.5 rounded mr-1 mb-1 font-mono">
                    {a}
                  </span>
                ))}
              </div>
            )}
            {report.extracted_entities.frameworks?.length > 0 && (
              <div>
                <span className="font-semibold text-slate-400 block mb-1">Frameworks & Libraries:</span>
                {report.extracted_entities.frameworks.map((f, i) => (
                  <span key={i} className="inline-block bg-teal-950 text-teal-200 border border-teal-800 px-2 py-0.5 rounded mr-1 mb-1 font-mono">
                    {f}
                  </span>
                ))}
              </div>
            )}
            {report.extracted_entities.datasets?.length > 0 && (
              <div>
                <span className="font-semibold text-slate-400 block mb-1">Datasets:</span>
                {report.extracted_entities.datasets.map((d, i) => (
                  <span key={i} className="inline-block bg-amber-950 text-amber-200 border border-amber-800 px-2 py-0.5 rounded mr-1 mb-1 font-mono">
                    {d}
                  </span>
                ))}
              </div>
            )}
            {report.extracted_entities.applications?.length > 0 && (
              <div>
                <span className="font-semibold text-slate-400 block mb-1">Applications:</span>
                {report.extracted_entities.applications.map((app, i) => (
                  <span key={i} className="inline-block bg-rose-950 text-rose-200 border border-rose-800 px-2 py-0.5 rounded mr-1 mb-1 font-mono">
                    {app}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Literature Trend Context */}
        <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-3">
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" /> Literature Trend (Semantic Scholar)
          </h3>
          {report.trend_context.trend_status === 'unavailable' ? (
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-slate-400 text-xs">
              Semantic Scholar live API status unavailable. Using historical corpus baselines.
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 bg-emerald-950/40 rounded-xl border border-emerald-800">
                <div className="text-slate-400">Topic Growth (YoY)</div>
                <div className="text-xl font-bold text-emerald-300 font-mono mt-1">+{report.trend_context.growth_rate_pct}%</div>
              </div>
              <div className="p-3.5 bg-blue-950/40 rounded-xl border border-blue-800">
                <div className="text-slate-400">Trend Status</div>
                <div className="text-xl font-bold text-blue-300 font-mono mt-1">{report.trend_context.trend_status}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 5: Most Similar Existing Projects */}
      {report.most_similar_projects.length > 0 && (
        <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-3">
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" /> Most Similar Existing Projects (Graph Overlap)
          </h3>
          <ul className="divide-y divide-slate-800 text-xs">
            {report.most_similar_projects.map((p, idx) => (
              <li key={idx} className="py-3 flex items-center justify-between gap-4">
                <div>
                  <span className="font-semibold text-slate-200 block">{p.title}</span>
                  <span className="text-[10px] text-slate-400 font-mono">ID: {p.project_id}</span>
                </div>
                <div className="text-right">
                  <span className="font-mono text-indigo-300 font-bold bg-indigo-950 px-2.5 py-1 rounded-lg border border-indigo-800">
                    {(p.similarity_score * 100).toFixed(1)}% Graph Similarity
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* SECTION 6: Module 7 Faculty Review Ground Truth Form */}
      <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-indigo-400" /> Module 7: Faculty Ground Truth Feedback
        </h3>
        {submitted ? (
          <div className="p-4 bg-emerald-950/80 text-emerald-200 rounded-xl text-xs font-medium border border-emerald-800">
            Thank you! Faculty rating has been submitted into <code className="font-mono text-emerald-300">AcadEval_FacultyEvaluation</code> to calibrate the graph engine.
          </div>
        ) : (
          <form onSubmit={handleFacultySubmit} className="space-y-3">
            <div className="flex items-center gap-4">
              <label className="text-xs font-medium text-slate-300">Faculty Rating (1 - 10):</label>
              <input
                type="number"
                min="1"
                max="10"
                value={facultyRating}
                onChange={(e) => {
  const value = Number(e.target.value);

  if (value >= 1 && value <= 10) {
    setFacultyRating(value);
  }
}}
                className="w-20 px-3 py-1.5 bg-slate-950 border border-slate-700 text-slate-100 rounded-lg text-sm font-bold text-center"
              />
            </div>
            <div>
              <textarea
                placeholder="Optional feedback / justification..."
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="w-full p-3 text-xs bg-slate-950 border border-slate-700 text-slate-100 rounded-xl focus:border-indigo-500 focus:outline-none"
                rows={2}
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-500 transition"
            >
              Submit Faculty Ground Truth Rating
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
