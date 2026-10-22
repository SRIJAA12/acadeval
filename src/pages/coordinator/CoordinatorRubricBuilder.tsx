import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRubrics, createRubric } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import { Plus, Trash2, Save, AlertCircle, CheckCircle, Scale, Clock } from 'lucide-react';
import type { RubricCriteria } from '../../types';
import clsx from 'clsx';

const CoordinatorRubricBuilder: React.FC = () => {
  const { data: rubrics, isLoading, isError } = useQuery({ queryKey: ['rubrics'], queryFn: getRubrics });

  const [rubricName, setRubricName] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [criteria, setCriteria] = useState<RubricCriteria[]>([
    { criteriaId: 'c1', name: 'Novelty', weight: 20, isRequired: true, description: '' },
    { criteriaId: 'c2', name: 'Feasibility', weight: 15, isRequired: true, description: '' },
    { criteriaId: 'c3', name: 'Completeness', weight: 15, isRequired: true, description: '' },
    { criteriaId: 'c4', name: 'Technical Depth', weight: 20, isRequired: true, description: '' },
    { criteriaId: 'c5', name: 'Clarity', weight: 15, isRequired: true, description: '' },
    { criteriaId: 'c6', name: 'Similarity Risk', weight: 5, isRequired: false, description: '' },
    { criteriaId: 'c7', name: 'Publication Potential', weight: 10, isRequired: false, description: '' },
  ]);
  const [saved, setSaved] = useState(false);

  const totalWeight = criteria.reduce((s, c) => s + c.weight, 0);
  const isValid = totalWeight === 100 && rubricName.trim().length > 0;

  const addCriteria = () => setCriteria(prev => [...prev, {
    criteriaId: `c_${Date.now()}`, name: '', weight: 0, isRequired: false, description: '',
  }]);

  const removeCriteria = (id: string) => setCriteria(prev => prev.filter(c => c.criteriaId !== id));

  const updateCriteria = (id: string, field: keyof RubricCriteria, value: string | number | boolean) => {
    setCriteria(prev => prev.map(c => c.criteriaId === id ? { ...c, [field]: value } : c));
  };

  const handleSave = async () => {
    await createRubric({ name: rubricName, department: 'CSE', academicYear: academicYear || undefined, criteria });
    setSaved(true);
  };

  if (isLoading) return <LoadingState message="Loading rubrics..." />;
  if (isError) return <ErrorState />;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">Rubrics</h1>
        <p className="text-slate-500 mt-1">Set the evaluation rubric reviewers use for grading. Every rubric still needs HOD approval before it's active.</p>
      </div>

      {/* Existing Rubrics */}
      {rubrics && rubrics.length > 0 && (
        <div className="card mb-6">
          <h2 className="font-semibold text-navy-900 mb-3">Rubrics</h2>
          <div className="space-y-2">
            {rubrics.map(r => (
              <div key={r.rubricId} className="flex items-center justify-between bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div>
                  <p className="font-medium text-slate-700">
                    {r.name} <span className="text-xs font-normal text-slate-400">v{r.version}</span>
                  </p>
                  <p className="text-xs text-slate-400">
                    {r.criteria.length} criteria · Created by {r.createdBy}
                    {r.academicYear && ` · ${r.academicYear}`}
                  </p>
                </div>
                <div>
                  {r.isApproved ? (
                    <span className="badge badge-teal"><CheckCircle size={11} /> Approved</span>
                  ) : (
                    <span className="badge badge-gold"><Clock size={11} /> Pending HOD Approval</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Builder */}
      {saved ? (
        <div className="card text-center py-10">
          <CheckCircle size={40} className="text-teal-500 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-navy-900">Rubric Saved!</h2>
          <p className="text-slate-500 text-sm mt-1">Sent to HOD for approval.</p>
          <button onClick={() => { setSaved(false); setRubricName(''); }} className="btn-primary mt-4">Build Another</button>
        </div>
      ) : (
        <div className="card space-y-5">
          <h2 className="font-semibold text-navy-900 flex items-center gap-2">
            <Scale size={18} className="text-indigo-500" /> Create New Rubric
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Rubric Name *</label>
              <input value={rubricName} onChange={e => setRubricName(e.target.value)} className="input" placeholder="e.g. CSE Final Year Project" />
            </div>
            <div>
              <label className="label">Academic Year</label>
              <input value={academicYear} onChange={e => setAcademicYear(e.target.value)} className="input" placeholder="e.g. 2025-26" />
            </div>
          </div>

          {/* Criteria table */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="label mb-0">Criteria</label>
              <div className={clsx(
                'text-sm font-semibold',
                totalWeight === 100 ? 'text-teal-600' : totalWeight > 100 ? 'text-red-500' : 'text-gold-500'
              )}>
                Total: {totalWeight}% {totalWeight !== 100 && '(must equal 100%)'}
              </div>
            </div>

            <div className="space-y-2">
              {criteria.map(c => (
                <div key={c.criteriaId} className="grid grid-cols-12 gap-2 items-center bg-slate-50 rounded-xl p-3 border border-slate-100">
                  <div className="col-span-4">
                    <input
                      value={c.name}
                      onChange={e => updateCriteria(c.criteriaId, 'name', e.target.value)}
                      className="input text-sm py-2"
                      placeholder="Criteria name"
                    />
                  </div>
                  <div className="col-span-5">
                    <input
                      value={c.description}
                      onChange={e => updateCriteria(c.criteriaId, 'description', e.target.value)}
                      className="input text-sm py-2"
                      placeholder="Description (optional)"
                    />
                  </div>
                  <div className="col-span-1">
                    <div className="relative">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={c.weight}
                        onChange={e => updateCriteria(c.criteriaId, 'weight', Number(e.target.value))}
                        className="input text-sm py-2 pr-6 text-center"
                      />
                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400">%</span>
                    </div>
                  </div>
                  <div className="col-span-1 flex items-center justify-center">
                    <input
                      type="checkbox"
                      checked={c.isRequired}
                      onChange={e => updateCriteria(c.criteriaId, 'isRequired', e.target.checked)}
                      className="w-4 h-4 accent-indigo-500"
                      title="Required"
                    />
                  </div>
                  <div className="col-span-1">
                    <button onClick={() => removeCriteria(c.criteriaId)} className="p-2 hover:bg-red-50 rounded-lg text-slate-300 hover:text-red-500 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button onClick={addCriteria} className="btn-outline mt-3 text-sm">
              <Plus size={15} /> Add Criteria
            </button>
          </div>

          {!isValid && rubricName.trim() && (
            <div className="flex items-center gap-2 text-gold-700 text-sm bg-gold-50 px-4 py-3 rounded-xl border border-gold-100">
              <AlertCircle size={16} /> Criteria weights must sum to exactly 100% before saving.
            </div>
          )}

          <button onClick={handleSave} disabled={!isValid} className="btn-primary">
            <Save size={16} /> Save Rubric (Send to HOD for Approval)
          </button>
        </div>
      )}
    </div>
  );
};

export default CoordinatorRubricBuilder;
