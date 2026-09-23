import React, { useState } from 'react';
import {
  Cpu, Database, Layers, Package, Server, Target, Wrench, BarChart2,
  ChevronDown, ChevronUp, AlertTriangle, CheckCircle, RefreshCw, Zap,
} from 'lucide-react';
import clsx from 'clsx';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ExtractedEntities {
  algorithms: string[];
  technologies: string[];
  frameworks: string[];
  libraries: string[];
  datasets: string[];
  applications: string[];
  hardware: string[];
  metrics: string[];
  unmatched_spans: string[];
  all_extracted?: { text: string; category: string; start: number; end: number }[];
}

interface EntityExtractionPanelProps {
  entities: ExtractedEntities | null | undefined;
  isLoading?: boolean;
  onReExtract?: () => void;   // faculty-only re-extract button
  showReExtract?: boolean;
}

// ── Category config ───────────────────────────────────────────────────────────

const CATEGORIES: {
  key: keyof Omit<ExtractedEntities, 'unmatched_spans' | 'all_extracted'>;
  label: string;
  icon: React.ReactNode;
  chipClass: string;
  dotClass: string;
}[] = [
  {
    key: 'algorithms',
    label: 'Algorithms',
    icon: <Cpu size={14} />,
    chipClass: 'bg-blue-50 text-blue-700 border-blue-200',
    dotClass: 'bg-blue-500',
  },
  {
    key: 'technologies',
    label: 'Technologies',
    icon: <Server size={14} />,
    chipClass: 'bg-violet-50 text-violet-700 border-violet-200',
    dotClass: 'bg-violet-500',
  },
  {
    key: 'frameworks',
    label: 'Frameworks',
    icon: <Layers size={14} />,
    chipClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    dotClass: 'bg-indigo-500',
  },
  {
    key: 'libraries',
    label: 'Libraries',
    icon: <Package size={14} />,
    chipClass: 'bg-sky-50 text-sky-700 border-sky-200',
    dotClass: 'bg-sky-500',
  },
  {
    key: 'datasets',
    label: 'Datasets',
    icon: <Database size={14} />,
    chipClass: 'bg-amber-50 text-amber-700 border-amber-200',
    dotClass: 'bg-amber-500',
  },
  {
    key: 'applications',
    label: 'Applications',
    icon: <Target size={14} />,
    chipClass: 'bg-teal-50 text-teal-700 border-teal-200',
    dotClass: 'bg-teal-500',
  },
  {
    key: 'hardware',
    label: 'Hardware',
    icon: <Wrench size={14} />,
    chipClass: 'bg-orange-50 text-orange-700 border-orange-200',
    dotClass: 'bg-orange-500',
  },
  {
    key: 'metrics',
    label: 'Metrics',
    icon: <BarChart2 size={14} />,
    chipClass: 'bg-rose-50 text-rose-700 border-rose-200',
    dotClass: 'bg-rose-500',
  },
];

// ── Chip component ────────────────────────────────────────────────────────────

const cleanAndDedupe = (items: string[]): string[] => {
  const seen = new Set<string>();
  const res: string[] = [];
  items.forEach(raw => {
    if (!raw || typeof raw !== 'string') return;
    let s = raw.replace(/\s*(?:(?:Mod|Component|Feature\s*(?:Component|Module|ScaleUnit|Unit|Pattern|Variation|Config|Cluster|Type|Instance|Sample))[\s\-_]*\d*|[\-_]\d{2,})\s*$/i, '').trim();
    s = s.replace(/\s+Feature$/i, '').trim();
    if (!s) s = raw.trim();

    const lower = s.toLowerCase();
    if (lower === 'rag' || lower.includes('retrieval-augmented generation') || lower.includes('retrieval augmented generation')) {
      s = 'Retrieval-Augmented Generation (RAG)';
    } else if (lower === 'nlp' || lower === 'natural language processing') {
      s = 'Natural Language Processing (NLP)';
    } else if (lower.includes('natural language processing toolkit') || lower === 'nltk') {
      s = 'NLTK';
    } else if (lower === 'cnn' || lower.includes('convolutional neural network')) {
      s = 'Convolutional Neural Network (CNN)';
    } else if (lower === 'rnn' || lower.includes('recurrent neural network')) {
      s = 'Recurrent Neural Network (RNN)';
    } else if (lower === 'f1' || lower === 'f1-score' || lower === 'f1 score') {
      s = 'F1-Score';
    } else if (lower === 'bert' || lower.includes('bidirectional encoder representations')) {
      s = 'BERT';
    }

    const key = s.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      res.push(s);
    }
  });
  return res.sort();
};

const EntityChip: React.FC<{ label: string; chipClass: string }> = ({ label, chipClass }) => (
  <span
    className={clsx(
      'inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-xs font-medium',
      'transition-all duration-150 hover:shadow-sm hover:scale-105 cursor-default select-none',
      chipClass
    )}
  >
    {label}
  </span>
);

// ── Stat badge ────────────────────────────────────────────────────────────────

const StatBadge: React.FC<{ count: number; dotClass: string }> = ({ count, dotClass }) => (
  <span className="flex items-center gap-1.5 text-xs text-slate-500">
    <span className={clsx('w-2 h-2 rounded-full', dotClass)} />
    {count}
  </span>
);

// ── Main component ────────────────────────────────────────────────────────────

const EntityExtractionPanel: React.FC<EntityExtractionPanelProps> = ({
  entities,
  isLoading = false,
  onReExtract,
  showReExtract = false,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [showRaw, setShowRaw] = useState(false);

  const totalEntities = entities
    ? CATEGORIES.reduce((sum, c) => sum + cleanAndDedupe(entities[c.key] ?? []).length, 0)
    : 0;

  const hasUnmatched = (entities?.unmatched_spans?.length ?? 0) > 0;

  if (isLoading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-slate-200 rounded-lg" />
          <div className="h-4 w-48 bg-slate-200 rounded" />
        </div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-6 w-20 bg-slate-100 rounded-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded); } }}
        className="w-full flex items-center justify-between p-5 hover:bg-slate-50 transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-sm">
            <Zap size={17} className="text-white" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-slate-800 text-sm">
              Extracted Entities
              <span className="ml-2 text-xs font-normal text-slate-400">Module 3</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {entities
                ? `${totalEntities} entities across ${CATEGORIES.filter(c => (entities[c.key]?.length ?? 0) > 0).length} categories`
                : 'Run submission to extract entities'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasUnmatched && (
            <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
              <AlertTriangle size={11} />
              {entities!.unmatched_spans.length} pending review
            </span>
          )}
          {entities && !hasUnmatched && totalEntities > 0 && (
            <span className="flex items-center gap-1 text-xs text-teal-600 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">
              <CheckCircle size={11} />
              Fully resolved
            </span>
          )}
          {showReExtract && onReExtract && (
            <button
              type="button"
              onClick={e => { e.stopPropagation(); onReExtract(); }}
              className="flex items-center gap-1.5 text-xs text-slate-600 bg-white border border-slate-200 px-3 py-1.5 rounded-lg hover:border-violet-300 hover:text-violet-700 transition-all duration-150"
            >
              <RefreshCw size={12} />
              Re-extract
            </button>
          )}
          {expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-slate-100">
          {!entities ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mb-3">
                <Zap size={22} className="text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-600">No extraction yet</p>
              <p className="text-xs text-slate-400 mt-1">Submit the project through the AcadEval+ pipeline to extract entities.</p>
            </div>
          ) : (
            <>
              {/* Category rows */}
              <div className="pt-3 space-y-3">
                {CATEGORIES.map(cat => {
                  const items = cleanAndDedupe(entities[cat.key] ?? []);
                  if (items.length === 0) return null;
                  return (
                    <div key={cat.key} className="flex gap-3">
                      <div className="flex items-center gap-1.5 w-28 flex-shrink-0 mt-0.5">
                        <span className={clsx('text-slate-400', cat.chipClass.split(' ')[1])}>
                          {cat.icon}
                        </span>
                        <span className="text-xs font-medium text-slate-500">{cat.label}</span>
                        <StatBadge count={items.length} dotClass={cat.dotClass} />
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {items.map(name => (
                          <EntityChip key={name} label={name} chipClass={cat.chipClass} />
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Unmatched spans */}
              {hasUnmatched && (
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={14} className="text-amber-600" />
                    <span className="text-xs font-semibold text-amber-700">
                      {entities.unmatched_spans.length} Unmatched Term{entities.unmatched_spans.length > 1 ? 's' : ''} — Pending Faculty Review
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {entities.unmatched_spans.map(span => (
                      <span
                        key={span}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-amber-300 bg-amber-100 text-xs font-medium text-amber-800"
                      >
                        ⚠️ {span}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-amber-600 mt-2">
                    These terms were not found in the FeatureKnowledgeBase. Faculty can approve them under <strong>Entity Review</strong>.
                  </p>
                </div>
              )}

              {/* Summary stats bar */}
              <div className="flex items-center gap-4 pt-1 border-t border-slate-100">
                <span className="text-xs text-slate-400">
                  Extracted via: spaCy EntityRuler → Regex → BERT similarity → Gemini LLM
                </span>
                <button
                  onClick={() => setShowRaw(!showRaw)}
                  className="ml-auto text-xs text-slate-400 hover:text-slate-600 transition-colors underline"
                >
                  {showRaw ? 'Hide' : 'Show'} raw spans
                </button>
              </div>

              {/* Raw all_extracted debug view */}
              {showRaw && entities.all_extracted && entities.all_extracted.length > 0 && (
                <div className="rounded-lg bg-slate-900 p-3 overflow-x-auto">
                  <pre className="text-xs text-slate-300 whitespace-pre-wrap">
                    {JSON.stringify(entities.all_extracted, null, 2)}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default EntityExtractionPanel;
