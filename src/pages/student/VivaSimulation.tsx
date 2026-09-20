import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { LoadingState } from '../../components/States';
import type { VivaQuestion, VivaAnswerResult, VivaReport } from '../../types';
import { getVivaReport, startVivaSession, submitVivaAnswer } from '../../api/endpoints';
import {
  BookOpen, ChevronRight, CheckCircle, Star, Brain,
  RotateCcw, Trophy, Loader2, Target, AlertTriangle, Lightbulb, Activity
} from 'lucide-react';
import clsx from 'clsx';

const DIFFICULTY_COLORS: Record<string, string> = {
  Easy: 'badge-teal',
  Medium: 'badge-gold',
  Hard: 'badge-red',
  Research: 'bg-purple-100 text-purple-700 border-purple-200',
};

const ScoreDots: React.FC<{ score: number; max?: number }> = ({ score, max = 5 }) => (
  <div className="flex gap-1.5">
    {Array.from({ length: max }).map((_, i) => (
      <div
        key={i}
        className={clsx(
          'w-3 h-3 rounded-full',
          i < Math.round(score) ? 'bg-teal-500' : 'bg-slate-200'
        )}
      />
    ))}
  </div>
);

const VivaSimulation: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const projectId = searchParams.get('projectId') || '';

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<VivaQuestion | null>(null);
  const [answer, setAnswer] = useState('');
  const [answersHistory, setAnswersHistory] = useState<VivaAnswerResult[]>([]);
  const [lastResult, setLastResult] = useState<VivaAnswerResult | null>(null);
  
  const [isComplete, setIsComplete] = useState(false);
  const [isStarted, setIsStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [report, setReport] = useState<VivaReport | null>(null);
  const [kcs, setKcs] = useState<number>(0.0);

  // 1. Start Adaptive Viva Session
  const handleStart = async () => {
    setIsLoading(true);
    try {
      const data = await startVivaSession(projectId);
      setSessionId(data.sessionId);
      setCurrentQuestion(data.firstQuestion);
      setIsStarted(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to start viva session. Make sure project has extracted entities.');
    } finally {
      setIsLoading(false);
    }
  };

  // 2. Submit Answer & Receive Adaptive Question
  const handleSubmitAnswer = async () => {
    if (!sessionId || !currentQuestion || answer.trim().length < 5) return;
    setIsSubmitting(true);

    try {
      const data = await submitVivaAnswer(sessionId, currentQuestion.questionId, answer.trim());

      setLastResult(data);
      setAnswersHistory(prev => [...prev, data]);
      setKcs(data.kcsAfterAnswer || 0.0);
      setAnswer('');

      if (data.sessionComplete || !data.nextQuestion) {
        setIsComplete(true);
        fetchFinalReport(sessionId);
      } else {
        setCurrentQuestion(data.nextQuestion);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to evaluate answer');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 3. Fetch Final Research-Grade Report
  const fetchFinalReport = async (sId: string) => {
    try {
      const data = await getVivaReport(sId);
      setReport(data);
    } catch (err) {
      console.error('Failed to fetch final report', err);
    }
  };

  if (!isStarted) {
    return (
      <div className="max-w-2xl mx-auto mt-8">
        <div className="card text-center py-12">
          <div className="w-20 h-20 bg-navy-50 rounded-full flex items-center justify-center mx-auto mb-5">
            <Brain size={36} className="text-navy-900" />
          </div>
          <h1 className="text-2xl font-display font-bold text-navy-900 mb-2">
            Adaptive Knowledge-Coverage Viva Engine
          </h1>
          <p className="text-slate-500 mb-6 max-w-md mx-auto">
            Dynamic Computerized Adaptive Testing (CAT). Generates contextual questions from your project's Knowledge Graph and evaluates Knowledge Coverage (KCS).
          </p>

          <div className="grid grid-cols-3 gap-4 mb-8 text-sm">
            {[
              { icon: <Target size={20} />, label: 'Knowledge Graph', sub: 'Extracted concepts' },
              { icon: <Activity size={20} />, label: 'Adaptive CAT', sub: 'Dynamic difficulty' },
              { icon: <Star size={20} />, label: 'KCS Metric', sub: 'Coverage score' },
            ].map(item => (
              <div key={item.label} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                <div className="flex items-center justify-center text-teal-500 mb-2">{item.icon}</div>
                <p className="font-semibold text-slate-700">{item.label}</p>
                <p className="text-xs text-slate-400 mt-0.5">{item.sub}</p>
              </div>
            ))}
          </div>

          <button onClick={handleStart} disabled={isLoading} className="btn-navy px-8 py-3 text-base">
            {isLoading ? <><Loader2 size={18} className="animate-spin" /> Building Question Pool...</> : <>Start Adaptive Viva <ChevronRight size={18} /></>}
          </button>
        </div>
      </div>
    );
  }

  if (isComplete && report) {
    return (
      <div className="max-w-3xl mx-auto mt-8 space-y-6">
        {/* Viva Overview Card */}
        <div className="card text-center py-10">
          <Trophy size={48} className="text-gold-500 mx-auto mb-4" />
          <h2 className="text-2xl font-display font-bold text-navy-900 mb-1">Adaptive Viva Complete!</h2>
          <p className="text-slate-500">{report.summaryStatement}</p>

          <div className="grid grid-cols-3 gap-4 my-6">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs text-slate-400 font-semibold uppercase">Overall Score</p>
              <p className="text-3xl font-bold text-navy-900 mt-1">{report.overallScore}%</p>
            </div>
            <div className="bg-teal-50 p-4 rounded-xl border border-teal-100">
              <p className="text-xs text-teal-600 font-semibold uppercase">Coverage (KCS)</p>
              <p className="text-3xl font-bold text-teal-700 mt-1">{report.kcs}%</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
              <p className="text-xs text-purple-600 font-semibold uppercase">Verdict Grade</p>
              <p className="text-2xl font-bold text-purple-700 mt-1">{report.grade}</p>
            </div>
          </div>

          <div className="flex gap-3 justify-center">
            <button onClick={() => navigate('/student/reports')} className="btn-primary">Back to Reports</button>
          </div>
        </div>

        {/* Knowledge Gaps & Recommendations */}
        {report.knowledgeGaps && report.knowledgeGaps.length > 0 && (
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="text-amber-500" size={20} />
              <h3 className="font-bold text-navy-900">Knowledge Gap Analysis</h3>
            </div>
            <div className="space-y-3">
              {report.knowledgeGaps.map((gap, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">{gap.concept}</p>
                    <p className="text-xs text-slate-400">{gap.category} • Difficulty: {gap.difficulty}</p>
                  </div>
                  <span className={clsx('badge', gap.gapSeverity === 'Critical' ? 'badge-red' : 'badge-gold')}>
                    {gap.gapSeverity}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {report.learningRecommendations && report.learningRecommendations.length > 0 && (
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="text-teal-500" size={20} />
              <h3 className="font-bold text-navy-900">Learning Recommendations</h3>
            </div>
            <ul className="space-y-2">
              {report.learningRecommendations.map((rec: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                  <span className="text-teal-500 font-bold">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  if (!currentQuestion) return <LoadingState message="Loading question..." />;

  return (
    <div className="max-w-2xl mx-auto mt-8 space-y-5">
      {/* Live KCS Header */}
      <div className="card py-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase">Knowledge Coverage Score (KCS)</p>
          <p className="text-2xl font-bold text-teal-600">{kcs}%</p>
        </div>
        <div className="text-right">
          <p className="text-xs font-semibold text-slate-400 uppercase">Target Concept</p>
          <span className="badge badge-navy mt-1">{currentQuestion.targetConcept || 'General'}</span>
        </div>
      </div>

      {/* Question Card */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <span className={clsx('badge', DIFFICULTY_COLORS[currentQuestion.difficulty] || 'badge-slate')}>
            {currentQuestion.difficulty}
          </span>
          <span className="badge badge-slate">{currentQuestion.category}</span>
        </div>
        <p className="text-lg font-semibold text-navy-900 leading-relaxed mb-6">{currentQuestion.text}</p>

        <label className="label">Your Technical Answer</label>
        <textarea
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          rows={6}
          className="input resize-none"
          placeholder="Explain technical details, architecture, trade-offs, and concepts..."
        />

        <button
          onClick={handleSubmitAnswer}
          disabled={isSubmitting || answer.trim().length < 5}
          className="btn-primary w-full justify-center mt-4 py-3"
        >
          {isSubmitting
            ? <><Loader2 size={16} className="animate-spin" /> Evaluating Answer...</>
            : <>Submit & Next Adaptive Question <ChevronRight size={16} /></>}
        </button>

        {/* Semantic Evaluation Result */}
        {lastResult && !isSubmitting && (
          <div className="mt-5 bg-slate-50 rounded-xl border border-slate-100 p-4 animate-fade-in space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-slate-500 uppercase">Semantic Evaluation</p>
              <div className="flex items-center gap-2">
                <p className="font-bold text-teal-700">{lastResult.score} / 5.0</p>
                <ScoreDots score={lastResult.score} />
              </div>
            </div>

            {lastResult.evaluation && (
              <div className="grid grid-cols-4 gap-2 text-center text-xs py-2 bg-white rounded-lg border border-slate-100">
                <div>
                  <p className="text-slate-400">Correctness</p>
                  <p className="font-semibold text-slate-700">{Math.round(lastResult.evaluation.correctness * 100)}%</p>
                </div>
                <div>
                  <p className="text-slate-400">Completeness</p>
                  <p className="font-semibold text-slate-700">{Math.round(lastResult.evaluation.completeness * 100)}%</p>
                </div>
                <div>
                  <p className="text-slate-400">Depth</p>
                  <p className="font-semibold text-slate-700">{Math.round(lastResult.evaluation.technicalDepth * 100)}%</p>
                </div>
                <div>
                  <p className="text-slate-400">Confidence</p>
                  <p className="font-semibold text-slate-700">{Math.round(lastResult.evaluation.confidence * 100)}%</p>
                </div>
              </div>
            )}

            <p className="text-sm text-slate-600 italic">{lastResult.feedback}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default VivaSimulation;
