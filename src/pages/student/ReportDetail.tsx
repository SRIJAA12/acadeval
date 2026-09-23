import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getEvaluationReport, getProjectEntities } from '../../api/endpoints';
import { useAuth } from '../../auth/AuthContext';
import { LoadingState, ErrorState } from '../../components/States';
import RadarChart from '../../components/RadarChart';
import ScoreGauge from '../../components/ScoreGauge';
import Badge from '../../components/Badge';
import AppealModal from '../../components/AppealModal';
import EntityExtractionPanel from '../../components/EntityExtractionPanel';
import type { PublicEvaluationReport } from '../../types';
import {
  AlertTriangle, CheckCircle, XCircle, Download, BookOpen,
  TrendingUp, ChevronDown, ChevronUp, Info, Lightbulb,
} from 'lucide-react';
import clsx from 'clsx';

const DIMENSION_KEYS = [
  { key: 'novelty', label: 'Novelty' },
  { key: 'feasibility', label: 'Feasibility' },
  { key: 'completeness', label: 'Completeness' },
  { key: 'technicalDepth', label: 'Technical Depth' },
  { key: 'clarity', label: 'Clarity' },
  { key: 'similarityRisk', label: 'Similarity Risk (lower is better)' },
  { key: 'publicationPotential', label: 'Publication Potential' },
];

const ScoreBar: React.FC<{ label: string; score: number | null; dimKey: string; projectId: string; onAppeal: (dim: string, score: number) => void }> = ({
  label, score, dimKey, onAppeal,
}) => {
  if (score === null) {
    return (
      <div className="flex items-center gap-4">
        <div className="w-32 text-sm font-medium text-slate-600 flex-shrink-0">{label}</div>
        <div className="flex-1 bg-slate-100 rounded-full h-2" />
        <span className="text-xs text-slate-400 w-12 text-right">N/A</span>
      </div>
    );
  }

  const isRisk = dimKey === 'similarityRisk';
  const favorable = isRisk ? 100 - score : score;
  const color = favorable >= 80 ? 'bg-teal-500' : favorable >= 60 ? 'bg-gold-500' : 'bg-red-500';
  const textColor = favorable >= 80 ? 'text-teal-700' : favorable >= 60 ? 'text-gold-700' : 'text-red-700';

  return (
    <div className="flex items-center gap-4 group">
      <div className="w-32 text-sm font-medium text-slate-600 flex-shrink-0">{label}</div>
      <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all duration-700', color)} style={{ width: `${score}%` }} />
      </div>
      <div className="flex items-center gap-2">
        <span className={clsx('text-sm font-bold w-8 text-right', textColor)}>{score}</span>
        <button
          onClick={() => onAppeal(dimKey, score)}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-xs text-slate-400 hover:text-gold-600 border border-slate-200 hover:border-gold-300 rounded-lg px-2 py-0.5"
        >
          Appeal
        </button>
      </div>
    </div>
  );
};

const WeekCard: React.FC<{ week: number; focus: string; actions: string[]; isLast: boolean }> = ({
  week, focus, actions, isLast,
}) => {
  const [expanded, setExpanded] = useState(week === 1);

  return (
    <div className="relative flex gap-4">
      {!isLast && <div className="absolute left-4 top-10 bottom-0 w-0.5 bg-slate-100" />}
      <div className="w-8 h-8 rounded-full bg-navy-900 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 z-10">
        {week}
      </div>
      <div className="flex-1 mb-6">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between bg-white rounded-xl border border-slate-100 px-4 py-3 hover:border-teal-200 transition-all text-left"
        >
          <div>
            <p className="text-xs text-slate-400 font-medium">WEEK {week}</p>
            <p className="font-semibold text-slate-800 text-sm">{focus}</p>
          </div>
          {expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
        </button>
        {expanded && (
          <div className="mt-2 bg-teal-50 rounded-xl border border-teal-100 p-3 space-y-1.5 animate-fade-in">
            {actions.map((action, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-teal-700">
                <CheckCircle size={14} className="text-teal-500 flex-shrink-0 mt-0.5" />
                {action}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ReportDetail: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [appealState, setAppealState] = useState<{ dim: string; score: number } | null>(null);

  const { data: report, isLoading, isError, refetch } = useQuery({
    queryKey: ['report', projectId],
    queryFn: () => getEvaluationReport(projectId!, user!.role),
    enabled: !!projectId && !!user,
  });

  const { data: entityData, isLoading: entitiesLoading } = useQuery({
    queryKey: ['project-entities', projectId],
    queryFn: () => getProjectEntities(projectId!),
    enabled: !!projectId,
  });

  if (isLoading) return <LoadingState message="Loading evaluation report..." />;
  if (isError || !report) return <ErrorState retry={refetch} />;

  const r = report as PublicEvaluationReport;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Preliminary Banner */}
      {r.isPreliminary ? (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-3">
          <Info size={22} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-amber-900 text-base">Evaluation Pending Faculty Review</p>
            <p className="text-sm text-amber-800 mt-1">
              Your submission has been parsed and evaluated by the AI engine. However, official scores and dimension breakdown are withheld until your project guide or reviewer finalizes and publishes the report.
            </p>
          </div>
        </div>
      ) : null}

      {/* Duplicate Warning */}
      {!r.isPreliminary && r.similarity?.isDuplicate && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800">High Similarity Detected</p>
            <p className="text-sm text-red-700 mt-1">
              Internal similarity: <strong>{r.similarity.internalScore}%</strong> | External: <strong>{r.similarity.externalScore}%</strong>.
              Your project may overlap with an existing submission. Please review your content for originality.
            </p>
          </div>
        </div>
      )}

      {/* Header Card */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-6 items-start">
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <Badge type="submission" value={r.submissionType} />
              <Badge type="domain" value={r.domain} />
              {!r.isPreliminary && r.noveltyVerdict && <Badge type="novelty" value={r.noveltyVerdict} />}
              {!r.isPreliminary && r.feasibilityRating && <Badge type="feasibility" value={r.feasibilityRating} />}
              {r.isPreliminary && <Badge type="pipeline" value="awaiting_review" />}
            </div>
            <h1 className="text-xl font-display font-bold text-navy-900 mb-2">{r.title}</h1>

            {/* Badges */}
            {!r.isPreliminary && r.badges && r.badges.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {r.badges.map(badge => <Badge key={badge} type="achievement" value={badge} />)}
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-6">
            {!r.isPreliminary && r.overallScore !== null && r.overallScore !== undefined ? (
              <ScoreGauge value={r.overallScore} grade={r.grade} size={160} />
            ) : (
              <div className="w-36 h-36 rounded-2xl bg-amber-50 border border-amber-200 flex flex-col items-center justify-center p-4 text-center">
                <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">Status</span>
                <span className="text-sm font-semibold text-amber-900 mt-1">Awaiting Review</span>
                <span className="text-[11px] text-amber-600 mt-1">Scores Hidden</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={() => navigate(`/student/viva?projectId=${r.projectId}`)} className="btn-navy">
            <BookOpen size={16} /> Viva Simulation
          </button>
          {!r.isPreliminary && (
            <button onClick={() => window.print()} className="btn-outline">
              <Download size={16} /> Download PDF
            </button>
          )}
        </div>
      </div>

      {/* Module 3 — Extracted Entities Panel */}
      <EntityExtractionPanel
        entities={entityData?.extracted_entities}
        isLoading={entitiesLoading}
      />
      {r.isPreliminary ? (
        <div className="card bg-slate-50 border-dashed border-2 border-slate-200 text-center py-12 px-6">
          <Info size={36} className="text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-slate-700 mb-1">Detailed Scoring & Roadmap Locked</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
            Dimension scores, radar charts, strengths/weaknesses, and the 6-week improvement roadmap will be accessible as soon as your guide publishes the final evaluation.
          </p>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" /> Awaiting Faculty Review & Publication
          </div>
        </div>
      ) : (
        <>
          {/* Two Columns: Radar + Scores */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4">Dimension Breakdown</h2>
              <RadarChart scores={r.dimensionScores} />
            </div>

            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-5">Score Details</h2>
              <div className="space-y-4">
                {DIMENSION_KEYS.map(({ key, label }) => (
                  <ScoreBar
                    key={key}
                    label={label}
                    score={r.dimensionScores[key as keyof typeof r.dimensionScores]}
                    dimKey={key}
                    projectId={r.projectId}
                    onAppeal={(dim, score) => setAppealState({ dim, score })}
                  />
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-4 flex items-center gap-1">
                <Info size={11} /> Hover over a dimension and click "Appeal" to dispute a score
              </p>
            </div>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4 flex items-center gap-2">
                <CheckCircle size={18} className="text-teal-500" /> Strengths
              </h2>
              <ul className="space-y-2">
                {r.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <div className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-1.5 flex-shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>

            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4 flex items-center gap-2">
                <XCircle size={18} className="text-red-400" /> Areas for Improvement
              </h2>
              <ul className="space-y-2">
                {r.weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Missing Sections */}
          {r.missingSections && r.missingSections.length > 0 && (
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4 flex items-center gap-2">
                <AlertTriangle size={18} className="text-gold-500" /> Missing Sections
              </h2>
              <div className="flex flex-wrap gap-2">
                {r.missingSections.map(s => (
                  <span key={s} className="badge badge-red">{s}</span>
                ))}
              </div>
            </div>
          )}

          {/* Percentile Ranks */}
          {r.percentileRanks && Object.keys(r.percentileRanks).length > 0 && (
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4 flex items-center gap-2">
                <TrendingUp size={18} className="text-teal-500" /> Historical Percentile Rankings
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(r.percentileRanks).map(([dim, pct]) => (
                  <div key={dim} className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                    <p className="text-xs text-slate-500 capitalize">{dim}</p>
                    <p className={clsx('text-2xl font-bold font-display mt-1',
                      pct >= 80 ? 'text-teal-600' : pct >= 50 ? 'text-gold-500' : 'text-red-500'
                    )}>Top {100 - pct}%</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Writing Quality */}
          {r.writingQuality && (
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4">Writing Quality Analysis</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <p className="text-xs text-slate-500">Readability Score</p>
                  <p className={clsx('text-2xl font-bold font-display mt-1',
                    (r.writingQuality.readability ?? 0) >= 60 ? 'text-teal-600' : 'text-gold-500'
                  )}>{r.writingQuality.readability ?? 'N/A'}</p>
                  <p className="text-xs text-slate-400">Flesch Reading Ease</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <p className="text-xs text-slate-500">Word Count</p>
                  <p className="text-2xl font-bold font-display text-navy-900 mt-1">{r.writingQuality.wordCount?.toLocaleString() ?? 'N/A'}</p>
                  <p className="text-xs text-slate-400">Total detected words</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <p className="text-xs text-slate-500">Passive Voice</p>
                  <p className={clsx('text-2xl font-bold font-display mt-1',
                    (r.writingQuality.passiveVoiceCount ?? 0) <= 10 ? 'text-teal-600' : 'text-gold-500'
                  )}>{r.writingQuality.passiveVoiceCount ?? 0}</p>
                  <p className="text-xs text-slate-400">instances found</p>
                </div>
              </div>
              {r.writingQuality.toneFlags && r.writingQuality.toneFlags.length > 0 && (
                <div className="mt-4 space-y-1.5">
                  {r.writingQuality.toneFlags.map((flag: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-slate-600 bg-slate-50 rounded-lg px-3 py-2">
                      <Info size={12} className="text-slate-400 flex-shrink-0" />
                      {flag}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Citations */}
          {r.citations && (
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-4">Citation Validator</h2>
              {r.citations.status === 'not_applicable' ? (
                <p className="text-sm text-slate-500">Citation analysis is available for full-document submissions.</p>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
                    <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                      <p className="text-xs text-slate-500">Parsed references</p>
                      <p className="text-xl font-bold text-navy-800">{r.citations.referenceCount}</p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                      <p className="text-xs text-slate-500">Externally verified</p>
                      <p className="text-xl font-bold text-navy-800">{r.citations.verifiedPercent}%</p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                      <p className="text-xs text-slate-500">Published in last 5 years</p>
                      <p className="text-xl font-bold text-navy-800">{r.citations.recentPercent}%</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">This checks reference verifiability and recency; it does not claim IEEE style compliance.</p>
                  {r.citations.issues && r.citations.issues.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs text-slate-500 font-medium">References needing attention:</p>
                      {r.citations.issues.map((issue, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
                          <XCircle size={13} /> {issue}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Versioned assessment evidence */}
          {r.assessmentEvidence && (
            <div className="card">
              <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
                <div>
                  <h2 className="text-base font-semibold text-navy-900">Assessment Evidence</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Scores are derived from detected submission evidence; missing evidence is shown as a gap.
                  </p>
                </div>
                <span className="badge badge-slate">{r.assessmentEvidence.evidence_quality.replaceAll('_', ' ')}</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(r.assessmentEvidence.feasibility.criteria).map(([name, criterion]) => (
                  <div key={name} className="bg-slate-50 rounded-xl border border-slate-100 p-3">
                    <div className="flex justify-between gap-3">
                      <p className="text-sm font-medium text-slate-700 capitalize">{name.replaceAll('_', ' ')}</p>
                      <span className="text-sm font-bold text-navy-800">{criterion.score}/100</span>
                    </div>
                    {criterion.evidence[0] && <p className="text-xs text-teal-700 mt-2">{criterion.evidence[0]}</p>}
                    {criterion.gaps[0] && <p className="text-xs text-gold-700 mt-2">Gap: {criterion.gaps[0]}</p>}
                  </div>
                ))}
              </div>
              {r.evaluationMethodVersion && (
                <p className="text-[11px] text-slate-400 mt-4">Method: {r.evaluationMethodVersion}</p>
              )}
            </div>
          )}

          {/* Improvement Roadmap */}
          {r.improvementRoadmap && r.improvementRoadmap.length > 0 && (
            <div className="card">
              <h2 className="text-base font-semibold text-navy-900 mb-6 flex items-center gap-2">
                <Lightbulb size={18} className="text-gold-500" /> Evidence-Based Improvement Roadmap
              </h2>
              <div>
                {r.improvementRoadmap.map((week, i) => (
                  <WeekCard
                    key={week.week}
                    week={week.week}
                    focus={week.focus}
                    actions={week.actions}
                    isLast={i === r.improvementRoadmap.length - 1}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Appeal Modal */}
      {appealState && (
        <AppealModal
          isOpen={true}
          onClose={() => setAppealState(null)}
          projectId={r.projectId}
          dimension={appealState.dim}
          currentScore={appealState.score}
        />
      )}
    </div>
  );
};

export default ReportDetail;
