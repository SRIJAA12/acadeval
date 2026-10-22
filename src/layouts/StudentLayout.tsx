import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  Upload, FileText, MessageSquare,
  BookOpen, User, LogOut, GraduationCap, ChevronRight, Users, ListChecks,
} from 'lucide-react';
import clsx from 'clsx';
import NotificationBell from '../components/NotificationBell';

const navItems = [
  { to: '/student/upload', icon: <Upload size={18} />, label: 'Submit Project' },
  { to: '/student/reports', icon: <FileText size={18} />, label: 'My Reports' },
  { to: '/student/discussion', icon: <MessageSquare size={18} />, label: 'Discussion & Progress' },
  { to: '/student/team-progress', icon: <Users size={18} />, label: 'Team Progress' },
  { to: '/student/todo', icon: <ListChecks size={18} />, label: 'To-Do' },
  { to: '/student/viva', icon: <BookOpen size={18} />, label: 'Viva Simulation' },
  { to: '/student/profile', icon: <User size={18} />, label: 'Profile' },
];

const StudentLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className={clsx(
        'fixed left-0 top-0 h-screen bg-navy-gradient flex flex-col z-40 transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10">
          <div className="w-9 h-9 rounded-xl bg-teal-500 flex items-center justify-center flex-shrink-0">
            <GraduationCap size={20} className="text-white" />
          </div>
          {sidebarOpen && (
            <div>
              <h1 className="text-white font-display font-bold text-lg leading-none">AcadEval</h1>
              <p className="text-white/40 text-[10px] font-medium mt-0.5">Student Portal</p>
            </div>
          )}
        </div>

        {/* Nav */}
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

        {/* User info */}
        <div className="border-t border-white/10 p-3">
          <div className={clsx('flex items-center gap-3', !sidebarOpen && 'justify-center')}>
            <div className="w-9 h-9 rounded-full bg-teal-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
              {user?.name?.charAt(0) || 'S'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{user?.name}</p>
                <p className="text-white/40 text-xs truncate">{user?.email}</p>
              </div>
            )}
            {sidebarOpen && (
              <button onClick={handleLogout} className="p-1.5 hover:bg-white/10 rounded-lg text-white/50 hover:text-white transition-colors">
                <LogOut size={15} />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className={clsx('flex-1 transition-all duration-300', sidebarOpen ? 'ml-64' : 'ml-16')}>
        {/* Topbar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-100 px-6 py-3 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <ChevronRight size={18} className={clsx('text-slate-500 transition-transform', sidebarOpen && 'rotate-180')} />
          </button>
          <div className="flex items-center gap-3">
            <NotificationBell />
          </div>
        </header>

        {/* Content */}
        <div className="p-6 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
};

export default StudentLayout;
