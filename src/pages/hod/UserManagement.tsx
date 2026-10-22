import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUsers, updateUserRole } from '../../api/endpoints';
import { LoadingState, ErrorState } from '../../components/States';
import { Search, UserCog, CheckCircle } from 'lucide-react';
import type { UserRole } from '../../types';
import clsx from 'clsx';

const ROLE_COLORS: Record<UserRole, string> = {
  student: 'badge-teal',
  guide: 'badge-gold',
  reviewer: 'badge-purple',
  hod: 'badge-navy',
  coordinator: 'badge-slate',
};

const UserManagement: React.FC = () => {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [editingUser, setEditingUser] = useState<string | null>(null);
  const [newRole, setNewRole] = useState<UserRole>('student');
  const [savedUser, setSavedUser] = useState<string | null>(null);

  const { data: users, isLoading, isError, refetch } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) => updateUserRole(userId, role),
    onSuccess: (_, vars) => {
      setSavedUser(vars.userId);
      setEditingUser(null);
      qc.invalidateQueries({ queryKey: ['users'] });
      setTimeout(() => setSavedUser(null), 2000);
    },
  });

  const filtered = (users || []).filter(u =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    (u.rollNo || '').includes(search)
  );

  if (isLoading) return <LoadingState message="Loading users..." />;
  if (isError) return <ErrorState retry={refetch} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-navy-900">User Management</h1>
        <p className="text-slate-500 mt-1">Assign and manage roles for all accounts in your department</p>
      </div>

      <div className="card mb-6">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, email, or roll number..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input pl-9"
          />
        </div>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Roll No</th>
              <th>Department</th>
              <th>Current Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(u => (
              <tr key={u.userId}>
                <td>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-navy-900 flex items-center justify-center text-white text-sm font-bold">
                      {u.name.charAt(0)}
                    </div>
                    <span className="font-medium text-slate-800">{u.name}</span>
                  </div>
                </td>
                <td><span className="text-sm text-slate-500">{u.email}</span></td>
                <td><span className="text-sm text-slate-400">{u.rollNo || '—'}</span></td>
                <td><span className="text-sm text-slate-500">{u.department}</span></td>
                <td>
                  {editingUser === u.userId ? (
                    <select
                      value={newRole}
                      onChange={e => setNewRole(e.target.value as UserRole)}
                      className="input w-auto text-sm py-1.5"
                    >
                      <option value="student">Student</option>
                      <option value="guide">Guide</option>
                      <option value="reviewer">Reviewer</option>
                      <option value="coordinator">Coordinator</option>
                      <option value="hod">HOD</option>
                    </select>
                  ) : (
                    <span className={`badge capitalize ${ROLE_COLORS[u.role]}`}>{u.role}</span>
                  )}
                </td>
                <td>
                  <span className={clsx('badge', u.isActive ? 'badge-teal' : 'badge-red')}>
                    {u.isActive ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  {savedUser === u.userId ? (
                    <span className="flex items-center gap-1 text-xs text-teal-600">
                      <CheckCircle size={13} /> Saved
                    </span>
                  ) : editingUser === u.userId ? (
                    <div className="flex gap-1">
                      <button
                        onClick={() => updateMutation.mutate({ userId: u.userId, role: newRole })}
                        className="btn-primary py-1 px-2 text-xs"
                        disabled={updateMutation.isPending}
                      >
                        Save
                      </button>
                      <button onClick={() => setEditingUser(null)} className="btn-ghost py-1 px-2 text-xs">Cancel</button>
                    </div>
                  ) : (
                    <button
                      onClick={() => { setEditingUser(u.userId); setNewRole(u.role); }}
                      className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-700"
                    >
                      <UserCog size={13} /> Change Role
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UserManagement;
