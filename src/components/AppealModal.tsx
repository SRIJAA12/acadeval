import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { X, MessageSquare, AlertCircle } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { submitAppeal } from '../api/endpoints';

const appealSchema = z.object({
  justification: z.string()
    .min(50, 'Please provide at least 50 characters of justification')
    .max(1000, 'Justification cannot exceed 1000 characters'),
});

type AppealFormData = z.infer<typeof appealSchema>;

interface AppealModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  dimension: string;
  currentScore: number;
  onSuccess?: () => void;
}

const DIMENSION_LABELS: Record<string, string> = {
  novelty: 'Novelty',
  feasibility: 'Feasibility',
  completeness: 'Completeness',
  technicalDepth: 'Technical Depth',
  clarity: 'Clarity',
  similarityRisk: 'Similarity Risk',
  publicationPotential: 'Publication Potential',
};

const AppealModal: React.FC<AppealModalProps> = ({
  isOpen,
  onClose,
  projectId,
  dimension,
  currentScore,
  onSuccess,
}) => {
  const [submitted, setSubmitted] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<AppealFormData>({
    resolver: zodResolver(appealSchema),
  });

  const justification = watch('justification', '');

  const mutation = useMutation({
    mutationFn: ({ justification }: AppealFormData) =>
      submitAppeal(projectId, dimension, currentScore, justification),
    onSuccess: () => {
      setSubmitted(true);
      onSuccess?.();
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg mx-4 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gold-50 flex items-center justify-center">
              <MessageSquare size={20} className="text-gold-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">Appeal Score</h2>
              <p className="text-sm text-slate-500">{DIMENSION_LABELS[dimension] || dimension}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        {submitted ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 mb-2">Appeal Submitted</h3>
            <p className="text-sm text-slate-500 mb-6">Your guide/reviewer will review your appeal and respond within 48 hours.</p>
            <button onClick={onClose} className="btn-primary">Close</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="p-6 space-y-5">
            {/* Score info */}
            <div className="bg-slate-50 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Dimension being appealed</p>
                  <p className="font-semibold text-slate-800">{DIMENSION_LABELS[dimension] || dimension}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-500">Current Score</p>
                  <p className="text-2xl font-bold text-navy-900">{currentScore}<span className="text-sm font-normal text-slate-400">/100</span></p>
                </div>
              </div>
            </div>

            {/* Justification */}
            <div>
              <label className="label">Your Justification *</label>
              <textarea
                {...register('justification')}
                rows={5}
                className={`input resize-none ${errors.justification ? 'border-red-300' : ''}`}
                placeholder="Explain why you believe this score should be reconsidered. Be specific — reference page numbers, sections, or specific contributions that may have been missed..."
              />
              <div className="flex items-center justify-between mt-1">
                {errors.justification ? (
                  <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle size={12} />{errors.justification.message}</p>
                ) : (
                  <span />
                )}
                <span className={`text-xs ${justification.length > 900 ? 'text-red-500' : 'text-slate-400'}`}>
                  {justification.length}/1000
                </span>
              </div>
            </div>

            <div className="bg-gold-50 rounded-xl p-3 border border-gold-100">
              <p className="text-xs text-gold-700">
                <strong>Note:</strong> Appeals are reviewed by your assigned guide/reviewer. Only the specific dimension score you appeal will be re-evaluated.
              </p>
            </div>

            {mutation.isError && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-4 py-3 rounded-xl">
                <AlertCircle size={16} /> Failed to submit appeal. Please try again.
              </div>
            )}

            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onClose} className="btn-outline flex-1">Cancel</button>
              <button type="submit" className="btn-primary flex-1" disabled={mutation.isPending}>
                {mutation.isPending ? 'Submitting...' : 'Submit Appeal'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default AppealModal;
