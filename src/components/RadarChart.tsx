import React from 'react';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { Radar } from 'react-chartjs-2';
import type { DimensionScores } from '../types';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface RadarChartProps {
  scores: DimensionScores;
  showComparison?: boolean;
  comparisonScores?: DimensionScores;
  comparisonLabel?: string;
  size?: 'sm' | 'md' | 'lg';
}

const LABELS = ['Novelty', 'Feasibility', 'Completeness', 'Tech Depth', 'Clarity', 'Originality', 'Pub. Potential'];

const extractValues = (s: DimensionScores) => [
  s.novelty ?? 0,
  s.feasibility ?? 0,
  s.completeness ?? 0,
  s.technicalDepth ?? 0,
  s.clarity ?? 0,
  s.similarityRisk === null ? 0 : 100 - s.similarityRisk,
  s.publicationPotential ?? 0,
];

const RadarChart: React.FC<RadarChartProps> = ({
  scores,
  showComparison,
  comparisonScores,
  comparisonLabel = 'Dept. Average',
  size = 'md',
}) => {
  const sizeMap = { sm: 280, md: 380, lg: 480 };
  const px = sizeMap[size];

  const data = {
    labels: LABELS,
    datasets: [
      {
        label: 'Your Score',
        data: extractValues(scores),
        backgroundColor: 'rgba(30, 127, 114, 0.15)',
        borderColor: 'rgba(30, 127, 114, 0.9)',
        borderWidth: 2.5,
        pointBackgroundColor: '#1E7F72',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
      },
      ...(showComparison && comparisonScores
        ? [{
            label: comparisonLabel,
            data: extractValues(comparisonScores),
            backgroundColor: 'rgba(201, 154, 58, 0.1)',
            borderColor: 'rgba(201, 154, 58, 0.8)',
            borderWidth: 2,
            borderDash: [5, 4],
            pointBackgroundColor: '#C99A3A',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
          }]
        : []),
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          font: { family: 'Inter', size: 12 },
          color: '#475569',
          boxWidth: 12,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: '#1B2A4A',
        titleFont: { family: 'Inter', size: 13 },
        bodyFont: { family: 'Inter', size: 12 },
        padding: 10,
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        callbacks: {
          label: (ctx: { dataset: { label?: string }; parsed: { r: number } }) =>
            `${ctx.dataset.label}: ${ctx.parsed.r}/100`,
        },
      },
    },
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: {
          stepSize: 20,
          color: '#94a3b8',
          font: { size: 10 },
          backdropColor: 'transparent',
        },
        grid: { color: 'rgba(148, 163, 184, 0.2)' },
        angleLines: { color: 'rgba(148, 163, 184, 0.2)' },
        pointLabels: {
          font: { family: 'Inter', size: 11.5, weight: 500 },
          color: '#334155',
        },
      },
    },
  };

  return (
    <div style={{ width: px, height: px, maxWidth: '100%' }} className="mx-auto">
      <Radar data={data} options={options} />
    </div>
  );
};

export default RadarChart;
