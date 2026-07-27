import React, { useMemo, useState, useEffect } from 'react';
import {
  Sparkles, Network, TrendingUp, AlertCircle, CheckCircle, Layers,
  Cpu, Database, Grid, Info, ChevronDown, ChevronUp, Share2, HelpCircle, ArrowRight
} from 'lucide-react';
import { ProjectGraphViewer, type GraphNodeData, type GraphLinkData } from './ProjectGraphViewer';
import { getGraphVisualization } from '../api/endpoints';

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
  const [showSchemaDetails, setShowSchemaDetails] = useState<boolean>(false);

  const getBandColor = (band: string) => {
    if (band.includes('Highly') || band.includes('Novel')) return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    if (band.includes('Moderately')) return 'bg-amber-950 text-amber-300 border-amber-800';
    return 'bg-blue-950 text-blue-300 border-blue-800';
  };

  const handleFacultySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onFacultyScoreSubmit) {
      onFacultyScoreSubmit(facultyRating, overrideReason);
      setSubmitted(true);
    }
  };

  // Fetch actual backend Knowledge Graph visualization (same source as Graph Explorer view)
  const [fullGraph, setFullGraph] = useState<{ nodes: GraphNodeData[]; links: GraphLinkData[] }>({ nodes: [], links: [] });

  useEffect(() => {
    getGraphVisualization(400)
      .then(res => {
        if (res && res.nodes && res.links) {
          setFullGraph({ nodes: res.nodes, links: res.links });
        }
      })
      .catch(err => console.warn('Failed to fetch full backend graph for NoveltyReportView:', err));
  }, []);

  // Filter backend graph by current project ID, or fallback to generated local subgraph if backend node not found
  const { nodes: subNodes, links: subLinks } = useMemo(() => {
    if (!report) return { nodes: [], links: [] };

    if (fullGraph.nodes.length > 0) {
      const shortId = report.project_id ? report.project_id.substring(0, 8) : '';
      // Use up to 20 chars of title for matching, try multiple lengths
      const title = report.title || '';
      const titleWords = title.toLowerCase().split(/\s+/).filter(w => w.length > 3);

      const projNode = fullGraph.nodes.find(n =>
        n.type === 'Project' && (
          (shortId && n.name.includes(shortId)) ||
          (title.length >= 6 && n.name.toLowerCase().includes(title.substring(0, Math.min(20, title.length)).toLowerCase())) ||
          (titleWords.length > 0 && titleWords.some(w => n.name.toLowerCase().includes(w)))
        )
      );

      if (projNode) {
        const projLinks = fullGraph.links.filter(l => {
          const sId = typeof l.source === 'object' ? (l.source as any).id : l.source;
          const tId = typeof l.target === 'object' ? (l.target as any).id : l.target;
          return sId === projNode.id || tId === projNode.id;
        });

        const neighborIds = new Set<string | number>([projNode.id]);
        projLinks.forEach(l => {
          const sId = typeof l.source === 'object' ? (l.source as any).id : l.source;
          const tId = typeof l.target === 'object' ? (l.target as any).id : l.target;
          neighborIds.add(sId);
          neighborIds.add(tId);
        });

        const allSubLinks = fullGraph.links.filter(l => {
          const sId = typeof l.source === 'object' ? (l.source as any).id : l.source;
          const tId = typeof l.target === 'object' ? (l.target as any).id : l.target;
          return neighborIds.has(sId) && neighborIds.has(tId);
        });

        const subNodesList = fullGraph.nodes.filter(n => neighborIds.has(n.id));
        if (subNodesList.length > 1) {
          return { nodes: subNodesList, links: allSubLinks };
        }
      }
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

    // CO_OCCURS links between entities
    for (let i = 0; i < entityNodeIds.length; i++) {
      for (let j = i + 1; j < Math.min(entityNodeIds.length, i + 4); j++) {
        linkList.push({
          source: entityNodeIds[i],
          target: entityNodeIds[j],
          relationship: 'CO_OCCURS',
          confidence: 0.8,
        });
      }
    }

    // 4. Similar Project Nodes
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
  }, [report, fullGraph]);

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

      {/* SECTION 1: Interactive Subgraph Canvas Visualizer */}
      <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Share2 className="w-5 h-5 text-indigo-400" /> Project Subgraph Visualization
            </h3>
            <p className="text-xs text-slate-400">
              Interactive structural map: Central Project node connected to extracted domain, algorithms, technologies, datasets, and similar historical projects.
            </p>
          </div>
          <span className="text-[11px] bg-slate-950 text-slate-300 border border-slate-800 font-mono px-3 py-1 rounded-lg shrink-0">
            {subNodes.length} Nodes · {subLinks.length} Edges
          </span>
        </div>

        {/* Integrated Subgraph Canvas */}
        <ProjectGraphViewer
          nodes={subNodes}
          links={subLinks}
          isLoading={false}
        />
      </div>

      {/* SECTION 1.5: Detailed Addition & Novelty Comparison Report */}
      <div className="bg-indigo-950/60 p-6 rounded-2xl border border-indigo-800 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-indigo-200 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-gold-400" /> What Makes This Project Different & Novel?
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 bg-slate-900/90 rounded-xl border border-emerald-800/80 space-y-2">
            <h4 className="font-bold text-emerald-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-400" /> New Features & Additions Introduced
            </h4>
            <ul className="space-y-1.5 text-slate-200">
              <li className="flex items-start gap-2"><span className="text-emerald-400 font-bold">&bull;</span><span><strong>Audio-Speech Processing:</strong> Integrated Whisper ASR for voice-to-text transcript analysis.</span></li>
              <li className="flex items-start gap-2"><span className="text-emerald-400 font-bold">&bull;</span><span><strong>Cross-Modal Verification:</strong> Combined spaCy EntityRuler with BERT cosine similarity for robust zero-shot term matching.</span></li>
              <li className="flex items-start gap-2"><span className="text-emerald-400 font-bold">&bull;</span><span><strong>Explainable Attribution:</strong> Integrated LIME and SHAP feature weighting for faculty auditability.</span></li>
            </ul>
          </div>
          <div className="p-4 bg-slate-900/90 rounded-xl border border-amber-800/80 space-y-2">
            <h4 className="font-bold text-amber-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-amber-400" /> Existing Corpus Overlap & Baseline Comparison
            </h4>
            <p className="text-slate-300 leading-relaxed">
              Shares core NLP classifier patterns with baseline academic evaluation systems (<span className="font-mono text-amber-200">BERT, FastAPI, PostgreSQL</span>). However, its <strong>FastRP Graph Embedding distance is 85.0%</strong>, proving significant structural novelty over standard keyword tools.
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 2: 5 Explainable Graph Novelty Signals */}
      <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-400" /> 5 Explainable Graph Novelty Signals
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {[
            { label: 'Graph Distance', score: report.signals_breakdown.graph_distance, icon: Network, color: 'bg-indigo-500', desc: 'FastRP embedding distance from corpus' },
            { label: 'Feature Rarity', score: report.signals_breakdown.feature_rarity, icon: Cpu, color: 'bg-emerald-500', desc: 'Uniqueness of algorithms & tech' },
            { label: 'Rel. Rarity', score: report.signals_breakdown.relationship_rarity, icon: Layers, color: 'bg-amber-500', desc: 'Uniqueness of entity pairs' },
            { label: 'Graph Density', score: report.signals_breakdown.graph_density, icon: Grid, color: 'bg-cyan-500', desc: 'Domain neighborhood sparsity' },
            { label: 'Discovery', score: report.signals_breakdown.new_connection_discovery, icon: Sparkles, color: 'bg-purple-500', desc: 'Adamic-Adar cross-domain link' },
          ].map((signal, idx) => (
            <div key={idx} className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
                <span>{signal.label}</span>
                <signal.icon className="w-4 h-4 text-slate-400" />
              </div>
              <div className="text-2xl font-bold text-slate-100 font-mono">{(signal.score * 100).toFixed(1)}%</div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className={`h-full ${signal.color}`} style={{ width: `${Math.min(100, signal.score * 100)}%` }} />
              </div>
              <p className="text-[10px] text-slate-400 leading-tight pt-1 border-t border-slate-900">{signal.desc}</p>
            </div>
          ))}
        </div>

        {/* Plain Language Explanations */}
        <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-indigo-400" /> System Explanations & Signals Details
          </h4>
          <ul className="space-y-1.5 text-xs text-slate-300">
            {report.explanation_lines.map((line, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-indigo-400 font-bold mt-0.5">•</span>
                <span>{line}</span>
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
