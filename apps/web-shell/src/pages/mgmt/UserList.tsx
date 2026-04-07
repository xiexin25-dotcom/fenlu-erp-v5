import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { UserCog } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

interface UserDetail {
  id: string; username: string; full_name: string; email: string | null;
  is_superuser: boolean; is_active: boolean; roles: string[];
}
interface RoleDef { id: string; code: string; name: string; }

export default function UserList() {
  const qc = useQueryClient();
  const { data: users, isLoading } = useQuery({ queryKey: ['users'], queryFn: () => api.get<UserDetail[]>('/auth/users') });
  const { data: roles } = useQuery({ queryKey: ['roles'], queryFn: () => api.get<RoleDef[]>('/auth/roles') });

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: '', full_name: '', password: '', role_id: '' });

  const columns: Column<UserDetail>[] = [
    { key: 'username', header: '用户名', className: 'font-mono' },
    { key: 'full_name', header: '姓名' },
    { key: 'roles', header: '角色', render: r =>
      r.roles.length > 0
        ? r.roles.map((role, i) => <span key={i} className="inline-block mr-1 px-2 py-0.5 text-[11px] rounded" style={{ background: 'var(--accent-light)', color: 'var(--accent)' }}>{role}</span>)
        : <span style={{ color: 'var(--fg-tertiary)' }}>未分配</span>
    },
    { key: 'is_superuser', header: '管理员', render: r =>
      r.is_superuser ? <span className="text-xs font-medium" style={{ color: 'var(--status-purple-fg)' }}>是</span> : <span style={{ color: 'var(--fg-tertiary)' }}>否</span>
    },
    { key: 'is_active', header: '状态', render: r => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="用户管理" subtitle="账号 + 角色 + 权限" icon={<UserCog size={22} strokeWidth={1.5} />}
        actionLabel="新建用户" onAction={() => setShowCreate(true)} />
      <DataTable<UserDetail> columns={columns} data={users || []} loading={isLoading} />

      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建用户" onSubmit={async () => {
        await api.post('/auth/users', {
          username: form.username, full_name: form.full_name, password: form.password,
          role_ids: form.role_id ? [form.role_id] : [],
        });
        qc.invalidateQueries({ queryKey: ['users'] });
        setForm({ username: '', full_name: '', password: '', role_id: '' });
      }}>
        <FormField label="用户名"><FormInput value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} placeholder="登录用户名" required /></FormField>
        <FormField label="姓名"><FormInput value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} placeholder="真实姓名" required /></FormField>
        <FormField label="密码"><FormInput type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="至少4位" required /></FormField>
        <FormField label="角色">
          <FormSelect value={form.role_id} onChange={e => setForm(f => ({ ...f, role_id: e.target.value }))}>
            <option value="">不分配角色</option>
            {(roles || []).map(r => <option key={r.id} value={r.id}>{r.name} ({r.code})</option>)}
          </FormSelect>
        </FormField>
      </FormDialog>
    </div>
  );
}
