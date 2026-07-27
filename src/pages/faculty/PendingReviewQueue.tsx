import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getPendingReviewEntities, approveEntityReview, rejectEntityReview,
  getKnowledgeBase,
} from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import {
  CheckCircle, XCircle, Search, Database, AlertTriangle,
  ChevronDown, Cpu, Layers, Package, Server, Target, Wrench, BarChart2,
  BookOpen, RefreshCw,
} from 'lucide-react';
import clsx from 'clsx';

// ── Types ─────────────────────────────────────────────────────────────────────

interface PendingItem {
  name: string;
  category: string;
  source_project_id?: string;
  queued_at?: string;
}

interface KBEntry {
  name: string;
  category: string;
  aliases: string[];
  first_seen_year?: number;
  description?: string;
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  algorithm: <Cpu size={14} />,
  technology: <Server size={14} />,
  framework: <Layers size={14} />,
  library: <Package size={14} />,
  dataset: <Database size={14} />,
  application: <Target size={14} />,
  hardware: <Wrench size={14} />,
  metric: <BarChart2 size={14} />,
};

const CATEGORY_COLORS: Record<string, string> = {
  algorithm: 'bg-blue-100 text-blue-700',
  technology: 'bg-violet-100 text-violet-700',
  framework: 'bg-indigo-100 text-indigo-700',
  library: 'bg-sky-100 text-sky-700',
  dataset: 'bg-amber-100 text-amber-700',
  application: 'bg-teal-100 text-teal-700',
  hardware: 'bg-orange-100 text-orange-700',
  metric: 'bg-rose-100 text-rose-700',
};

// ── Approve modal ─────────────────────────────────────────────────────────────

const ApproveModal: React.FC<{
  item: PendingItem;
  onClose: () => void;
  onApprove: (payload: {
    category: string; aliases: string[]; first_seen_year?: number; description?: string;
  }) => void;
  isLoading: boolean;
}> = ({ item, onClose, onApprove, isLoading }) => {
  const [category, setCategory] = useState(item.category || 'technology');
  const [aliasInput, setAliasInput] = useState('');
  const [aliases, setAliases] = useState<string[]>([]);
  const [year, setYear] = useState('');
  const [description, setDescription] = useState('');

  const addAlias = () => {
    const a = aliasInput.trim();
    if (a && !aliases.includes(a)) setAliases(prev => [...prev, a]);
    setAliasInput('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-fade-in">
        <h3 className="text-lg font-semibold text-slate-800 mb-1">Approve Entity</h3>
        <p className="text-sm text-slate-500 mb-5">
          Adding <strong className="text-slate-700">{item.name}</strong> to the FeatureKnowledgeBase.
        </p>

        <div className="space-y-4">
          {/* Category */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Category</label>
            <div className="relative">
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-violet-300"
              >
                {Object.keys(CATEGORY_ICONS).map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {/* Aliases */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Aliases (optional)</label>
            <div className="flex gap-2">
              <input
                value={aliasInput}
                onChange={e => setAliasInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addAlias())}
                placeholder="e.g. CNN, ConvNet…"
                className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
              />
              <button
                onClick={addAlias}
                className="px-3 py-2 bg-violet-50 border border-violet-200 rounded-xl text-violet-700 text-xs font-semibold hover:bg-violet-100 transition-colors"
              >
                Add
              </button>
            </div>
            {aliases.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {aliases.map(a => (
                  <span key={a} className="flex items-center gap-1 px-2 py-0.5 bg-slate-100 rounded-full text-xs text-slate-600">
                    {a}
                    <button onClick={() => setAliases(prev => prev.filter(x => x !== a))} className="text-slate-400 hover:text-red-500">×</button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* First seen year */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">First Published Year (optional)</label>
            <input
              type="number" min="1950" max="2030"
              value={year}
              onChange={e => setYear(e.target.value)}
              placeholder="e.g. 2017"
              className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Short Description (optional)</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={2}
              placeholder="One-line description…"
              className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-violet-300"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 border border-slate-200 rounded-xl py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => onApprove({ category, aliases, first_seen_year: year ? parseInt(year) : undefined, description: description || undefined })}
            disabled={isLoading}
            className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 text-white rounded-xl py-2.5 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {isLoading ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle size={14} />}
            Approve & Add to KB
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Main Page ─────────────────────────────────────────────────────────────────

const PendingReviewQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'pending' | 'browse'>('pending');
  const [approveTarget, setApproveTarget] = useState<PendingItem | null>(null);
  const [kbSearch, setKbSearch] = useState('');
  const [kbCategory, setKbCategory] = useState('');

  const pendingQuery = useQuery({
    queryKey: ['entity-pending'],
    queryFn: getPendingReviewEntities,
  });

  const kbQuery = useQuery({
    queryKey: ['entity-kb', kbCategory, kbSearch],
    queryFn: () => getKnowledgeBase({ category: kbCategory || undefined, search: kbSearch || undefined }),
    enabled: activeTab === 'browse',
  });

  const approveMutation = useMutation({
    mutationFn: ({ name, payload }: { name: string; payload: object }) =>
      approveEntityReview(name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-pending'] });
      queryClient.invalidateQueries({ queryKey: ['entity-kb'] });
      setApproveTarget(null);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (name: string) => rejectEntityReview(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['entity-pending'] }),
  });

  const pending: PendingItem[] = (pendingQuery.data as { items: PendingItem[] })?.items ?? [];
  const kbEntries: KBEntry[] = (kbQuery.data as { entries: KBEntry[] })?.entries ?? [];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-900">Entity Knowledge Base</h1>
          <p className="text-slate-500 text-sm mt-1">
            Review new entity candidates flagged by Module 3's LLM pass and browse the FeatureKnowledgeBase.
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-xl">
          <AlertTriangle size={14} className="text-amber-600" />
          <span className="text-sm font-semibold text-amber-700">
            {pendingQuery.isLoading ? '…' : pending.length} pending
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit">
        {(['pending', 'browse'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
              activeTab === tab
                ? 'bg-white shadow-sm text-slate-800'
                : 'text-slate-500 hover:text-slate-700'
            )}
          >
            {tab === 'pending' ? (
              <span className="flex items-center gap-2">
                <AlertTriangle size={13} />
                Pending Review
                {pending.length > 0 && (
                  <span className="bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">{pending.length}</span>
                )}
              </span>
            ) : (
              <span className="flex items-center gap-2"><BookOpen size={13} /> Browse KB</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Pending Review Tab ── */}
      {activeTab === 'pending' && (
        <>
          {pendingQuery.isLoading && <LoadingState />}
          {pendingQuery.isError && <ErrorState message="Failed to load pending entities." retry={() => pendingQuery.refetch()} />}
          {!pendingQuery.isLoading && pending.length === 0 && (
            <div className="card flex flex-col items-center justify-center py-16 text-center">
              <CheckCircle size={40} className="text-teal-400 mb-3" />
              <p className="font-semibold text-slate-700">All clear!</p>
              <p className="text-sm text-slate-400 mt-1">No entity candidates pending review.</p>
            </div>
          )}
          {pending.length > 0 && (
            <div className="space-y-3">
              {pending.map(item => (
                <div key={item.name} className="card p-4 flex items-center gap-4 hover:shadow-md transition-shadow">
                  {/* Category badge */}
                  <div className={clsx(
                    'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold shrink-0',
                    CATEGORY_COLORS[item.category?.toLowerCase()] ?? 'bg-slate-100 text-slate-600'
                  )}>
                    {CATEGORY_ICONS[item.category?.toLowerCase()] ?? <Database size={14} />}
                    {item.category || 'unknown'}
                  </div>

                  {/* Name */}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-800 truncate">{item.name}</p>
                    {item.source_project_id && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        Flagged from project: <span className="font-mono">{item.source_project_id.slice(0, 8)}…</span>
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => rejectMutation.mutate(item.name)}
                      disabled={rejectMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 border border-red-200 text-red-600 text-xs font-semibold rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      <XCircle size={13} /> Reject
                    </button>
                    <button
                      onClick={() => setApproveTarget(item)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white text-xs font-semibold rounded-lg hover:bg-violet-700 transition-colors"
                    >
                      <CheckCircle size={13} /> Approve
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Browse KB Tab ── */}
      {activeTab === 'browse' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={kbSearch}
                onChange={e => setKbSearch(e.target.value)}
                placeholder="Search entities…"
                className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
              />
            </div>
            <div className="relative">
              <select
                value={kbCategory}
                onChange={e => setKbCategory(e.target.value)}
                className="border border-slate-200 rounded-xl px-3 pr-8 py-2.5 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-violet-300 bg-white"
              >
                <option value="">All categories</option>
                {Object.keys(CATEGORY_ICONS).map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {kbQuery.isLoading && <LoadingState />}
          {!kbQuery.isLoading && (
            <div className="card overflow-hidden">
              <div className="divide-y divide-slate-100">
                {kbEntries.length === 0 ? (
                  <div className="py-12 text-center text-slate-400 text-sm">No entries found.</div>
                ) : kbEntries.map(entry => (
                  <div key={entry.name} className="flex items-center gap-4 px-4 py-3 hover:bg-slate-50 transition-colors">
                    <span className={clsx(
                      'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-semibold shrink-0',
                      CATEGORY_COLORS[entry.category?.toLowerCase()] ?? 'bg-slate-100 text-slate-600'
                    )}>
                      {CATEGORY_ICONS[entry.category?.toLowerCase()] ?? <Database size={12} />}
                      {entry.category}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800">{entry.name}</p>
                      {entry.aliases?.length > 0 && (
                        <p className="text-xs text-slate-400 truncate">also: {entry.aliases.join(', ')}</p>
                      )}
                    </div>
                    {entry.first_seen_year && (
                      <span className="text-xs text-slate-400 shrink-0">{entry.first_seen_year}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {!kbQuery.isLoading && (
            <p className="text-xs text-slate-400 text-right">
              Showing {kbEntries.length} of {(kbQuery.data as { total?: number })?.total ?? 0} entries
            </p>
          )}
        </div>
      )}

      {/* Approve modal */}
      {approveTarget && (
        <ApproveModal
          item={approveTarget}
          onClose={() => setApproveTarget(null)}
          onApprove={payload => approveMutation.mutate({ name: approveTarget.name, payload })}
          isLoading={approveMutation.isPending}
        />
      )}
    </div>
  );
};

export default PendingReviewQueue;
