import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getNotifications, getUnreadNotificationCount, markNotificationRead, markAllNotificationsRead } from '../api/endpoints';
import { Bell, CheckCheck } from 'lucide-react';
import clsx from 'clsx';

const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { data: unreadCount } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: getUnreadNotificationCount,
    refetchInterval: 20000,
  });

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => getNotifications(20),
    enabled: open,
  });

  const readMutation = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });

  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="relative p-2 hover:bg-slate-100 rounded-xl transition-colors"
      >
        <Bell size={18} className="text-slate-500" />
        {!!unreadCount && (
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-100 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <p className="font-semibold text-sm text-navy-900">Notifications</p>
            {!!notifications?.length && (
              <button
                onClick={() => readAllMutation.mutate()}
                className="text-xs text-teal-600 hover:text-teal-700 flex items-center gap-1"
              >
                <CheckCheck size={13} /> Mark all read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {!notifications?.length && (
              <p className="text-sm text-slate-400 text-center py-8">No notifications yet.</p>
            )}
            {notifications?.map(n => (
              <button
                key={n.notificationId}
                onClick={() => {
                  if (!n.isRead) readMutation.mutate(n.notificationId);
                  if (n.link) { navigate(n.link); setOpen(false); }
                }}
                className={clsx(
                  'w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors',
                  !n.isRead && 'bg-teal-50/50'
                )}
              >
                <div className="flex items-start gap-2">
                  {!n.isRead && <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-1.5 flex-shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{n.title}</p>
                    {n.body && <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.body}</p>}
                    <p className="text-[10px] text-slate-400 mt-1">{new Date(n.createdAt).toLocaleString()}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
