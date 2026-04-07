import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { mgmtApi, type GLAccount } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const typeLabels: Record<string, string> = {
  ASSET: '资产', LIABILITY: '负债', EQUITY: '权益', REVENUE: '收入',
  EXPENSE: '费用', asset: '资产', liability: '负债', equity: '权益',
  revenue: '收入', expense: '费用',
};

const columns: Column<GLAccount>[] = [
  { key: 'code', header: '科目编码', className: 'font-mono' },
  { key: 'name', header: '科目名称' },
  { key: 'account_type', header: '类型', render: r => typeLabels[r.account_type] || r.account_type },
  { key: 'level', header: '级别', className: 'w-16' },
  { key: 'is_active', header: '状态', render: r => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
];

export default function GLAccountList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', account_type: 'ASSET', level: '1' });

  const { data, isLoading } = useQuery({ queryKey: ['gl-accounts'], queryFn: mgmtApi.listAccounts });

  return (
    <div className="p-6">
      <PageHeader
        title="总账科目"
        subtitle="GL Accounts"
        icon={<FileText className="text-indigo-500" size={24} />}
        actionLabel="新建科目"
        onAction={() => setShowCreate(true)}
      />
      <DataTable<GLAccount>
        columns={columns}
        data={data || []}
        loading={isLoading}
      />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建科目" onSubmit={async () => {
        await mgmtApi.createAccount({ ...form, level: Number(form.level) });
        qc.invalidateQueries({ queryKey: ['gl-accounts'] });
        setForm({ code: '', name: '', account_type: 'ASSET', level: '1' });
      }}>
        <FormField label="科目编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="科目名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="类型">
          <FormSelect value={form.account_type} onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))}>
            <option value="ASSET">资产</option>
            <option value="LIABILITY">负债</option>
            <option value="EQUITY">权益</option>
            <option value="REVENUE">收入</option>
            <option value="EXPENSE">费用</option>
          </FormSelect>
        </FormField>
        <FormField label="级别"><FormInput type="number" value={form.level} onChange={e => setForm(f => ({ ...f, level: e.target.value }))} min="1" max="5" /></FormField>
      </FormDialog>
    </div>
  );
}
