import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { GraduationCap, Eye, EyeOff, AlertCircle, Sparkles } from 'lucide-react';
import type { UserRole } from '../../types';

const ROLES: { value: UserRole; label: string; description: string; color: string }[] = [
  { value: 'student', label: 'Student', description: 'Submit projects, view feedback & viva', color: 'border-teal-500 bg-teal-50 text-teal-700' },
  { value: 'guide', label: 'Guide', description: 'Review assigned student projects', color: 'border-gold-500 bg-gold-50 text-gold-700' },
  { value: 'reviewer', label: 'Reviewer', description: 'Evaluate panel-assigned projects', color: 'border-purple-500 bg-purple-50 text-purple-700' },
  { value: 'hod', label: 'HOD', description: 'Department-wide oversight & admin', color: 'border-navy-700 bg-navy-50 text-navy-900' },
];

const roleDashboards: Record<UserRole, string> = {
  student: '/student/reports',
  guide: '/faculty/dashboard',
  reviewer: '/faculty/dashboard',
  hod: '/hod/overview',
};

const Login: React.FC = () => {
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [selectedRole, setSelectedRole] = useState<UserRole>('student');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isAuthenticated && user) {
      navigate(roleDashboards[user.role], { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  // Pre-fill demo credentials based on role
  useEffect(() => {
    const demoEmails: Record<UserRole, string> = {
      student: 'priya@college.edu',
      guide: 'meera@college.edu',
      reviewer: 'suresh@college.edu',
      hod: 'hod@college.edu',
    };
    setEmail(demoEmails[selectedRole]);
    setPassword('demo123');
  }, [selectedRole]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password, selectedRole);
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname;
      navigate(from || roleDashboards[selectedRole], { replace: true });
    } catch (err) {
      setError('Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-gradient flex">
      {/* Left Panel */}
      <div className="hidden lg:flex flex-1 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500 flex items-center justify-center">
            <GraduationCap size={22} className="text-white" />
          </div>
          <span className="text-white font-display font-bold text-xl">AcadEval</span>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={18} className="text-gold-400" />
            <span className="text-gold-400 text-sm font-semibold uppercase tracking-wider">AI-Powered Evaluation</span>
          </div>
          <h2 className="text-5xl font-display font-bold text-white leading-tight mb-6">
            Smarter Project<br />Evaluation for<br />
            <span className="text-gradient-gold">Engineering Colleges</span>
          </h2>
          <p className="text-white/60 text-lg leading-relaxed max-w-md">
            Holistic AI assessment covering novelty, feasibility, completeness,
            technical depth, and publication potential — with explainable scores
            and a personalized improvement roadmap.
          </p>

          <div className="mt-10 grid grid-cols-2 gap-4">
            {[
              { label: 'Graph Novelty', sub: 'Five explainable structural signals' },
              { label: 'Faculty Validation', sub: 'Human review remains the final decision' },
              { label: 'Entity Extraction', sub: 'Algorithms, datasets, tools, and relations' },
              { label: 'Async Processing', sub: 'Persistent project and batch progress' },
            ].map(item => (
              <div key={item.label} className="bg-white/5 rounded-2xl p-4 border border-white/10">
                <p className="text-white font-semibold text-sm">{item.label}</p>
                <p className="text-white/40 text-xs mt-1">{item.sub}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="text-white/30 text-sm">© 2025 AcadEval · Built for Engineering Excellence</p>
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 lg:max-w-md flex flex-col items-center justify-center p-8 bg-white lg:rounded-l-3xl">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-teal-500 flex items-center justify-center">
              <GraduationCap size={22} className="text-white" />
            </div>
            <span className="text-navy-900 font-display font-bold text-xl">AcadEval</span>
          </div>

          <h2 className="text-2xl font-display font-bold text-navy-900 mb-1">Welcome back</h2>
          <p className="text-slate-500 text-sm mb-8">Sign in to your account to continue</p>

          {/* Role Selector */}
          <div className="mb-6">
            <label className="label mb-2">I am a...</label>
            <div className="grid grid-cols-2 gap-2">
              {ROLES.map(role => (
                <button
                  key={role.value}
                  type="button"
                  onClick={() => setSelectedRole(role.value)}
                  className={`p-3 rounded-xl border-2 text-left transition-all duration-150 ${
                    selectedRole === role.value
                      ? role.color + ' border-current'
                      : 'border-slate-100 bg-white text-slate-500 hover:border-slate-200'
                  }`}
                >
                  <p className="font-semibold text-sm">{role.label}</p>
                  <p className="text-xs mt-0.5 opacity-70 leading-tight">{role.description}</p>
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="input"
                placeholder="your@college.edu"
                required
              />
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="input pr-11"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-4 py-3 rounded-xl border border-red-100">
                <AlertCircle size={16} /> {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full justify-center py-3 text-base"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 bg-slate-50 rounded-xl p-4 border border-slate-100">
            <p className="text-xs text-slate-500 font-medium mb-1">Demo credentials (auto-filled):</p>
            <p className="text-xs text-slate-700 font-mono font-medium">
              {email || 'Select a role above'} <span className="text-slate-400">/</span> demo123
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
