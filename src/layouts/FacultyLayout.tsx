import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  LayoutDashboard, Users, Inbox, ClipboardList, Upload,
  BarChart2, Settings, LogOut, GraduationCap, ChevronRight,
  Bell, Scale, History, MessageSquare, FlaskConical, Network, Award,
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { to: '/faculty/dashboard', icon: <LayoutDashboard size={18} />, label: 'Dashboard' },
  { to: '/faculty/submissions', icon: <Users size={18} />, label: 'All Submissions' },
  { to: '/faculty/queue', icon: <Inbox size={18} />, label: 'Review Queue' },
  { to: '/faculty/publications', icon: <Award size={18} />, label: 'Publications' },
  { to: '/faculty/batch', icon: <Upload size={18} />, label: 'Batch Upload' },
  { to: '/faculty/comparison', icon: <BarChart2 size={18} />, label: 'Comparison Table' },
  { to: '/faculty/rubric', icon: <Scale size={18} />, label: 'Rubric Builder' },
  { to: '/faculty/appeals', icon: <MessageSquare size={18} />, label: 'Appeals Inbox' },
  { to: '/faculty/benchmarks', icon: <History size={18} />, label: 'Benchmarks' },
  { to: '/faculty/entity-review', icon: <FlaskConical size={18} />, label: 'Entity Review' },
  { to: '/faculty/graph-explorer', icon: <Network size={18} />, label: 'Graph Explorer' },
];

const FacultyLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const isReviewer = user?.role === 'reviewer';
  const roleLabel = isReviewer ? 'Reviewer Portal' : 'Guide Portal';

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className={clsx(
        'fixed left-0 top-0 h-screen bg-navy-gradient flex flex-col z-40 transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}>
        <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10">
          <div className="w-9 h-9 rounded-xl bg-teal-500 flex items-center justify-center flex-shrink-0">
            <GraduationCap size={20} className="text-white" />
          </div>
          {sidebarOpen && (
            <div>
              <h1 className="text-white font-display font-bold text-lg leading-none">AcadEval</h1>
              <p className="text-white/40 text-[10px] font-medium mt-0.5">{roleLabel}</p>
            </div>
          )}
        </div>

        <nav className="flex-1 py-4 space-y-1 overflow-y-auto scrollbar-hide">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx('sidebar-link', isActive && 'active', !sidebarOpen && 'justify-center px-0 mx-3')
              }
            >
              {item.icon}
              {sidebarOpen && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className={clsx('flex items-center gap-3', !sidebarOpen && 'justify-center')}>
            <div className="w-9 h-9 rounded-full bg-gold-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
              {user?.name?.charAt(0) || 'F'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{user?.name}</p>
                <p className="text-white/40 text-xs capitalize">{user?.role}</p>
              </div>
            )}
            {sidebarOpen && (
              <button onClick={() => { logout(); navigate('/login'); }} className="p-1.5 hover:bg-white/10 rounded-lg text-white/50 hover:text-white transition-colors">
                <LogOut size={15} />
              </button>
            )}
          </div>
        </div>
      </aside>

      <main className={clsx('flex-1 transition-all duration-300', sidebarOpen ? 'ml-64' : 'ml-16')}>
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-100 px-6 py-3 flex items-center justify-between">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-slate-100 rounded-xl transition-colors">
            <ChevronRight size={18} className={clsx('text-slate-500 transition-transform', sidebarOpen && 'rotate-180')} />
          </button>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-gold-50 text-gold-700 rounded-full text-xs font-semibold capitalize border border-gold-200">
              {user?.role}
            </span>
            <button className="relative p-2 hover:bg-slate-100 rounded-xl transition-colors">
              <Bell size={18} className="text-slate-500" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
            </button>
          </div>
        </header>

        <div className="p-6 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
};

export default FacultyLayout;
