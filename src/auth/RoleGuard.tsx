import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { UserRole } from '../types';

const roleDashboards: Record<UserRole, string> = {
  student: '/student/reports',
  guide: '/faculty/dashboard',
  reviewer: '/faculty/dashboard',
  hod: '/hod/overview',
  coordinator: '/coordinator/overview',
};

interface RoleGuardProps {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}

const RoleGuard: React.FC<RoleGuardProps> = ({ allowedRoles, children }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-navy-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-white/70 text-sm">Loading AcadEval...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    const redirectTo = roleDashboards[user.role];
    return <Navigate to={redirectTo} state={{ unauthorized: true, from: location.pathname }} replace />;
  }

  return <>{children}</>;
};

export default RoleGuard;
