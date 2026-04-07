import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Truck, Search } from 'lucide-react';
import { scmApi, type Supplier } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const columns: Column<Supplier>[] = [
  { key: 'code', header: '供应商编码', className: 'font-mono' },
  { key: 'name', header: '供应商名称' },
  { key: 'tier', header: '等级', render: r => <StatusBadge status={r.tier} /> },
  { key: 'contact_name', header: '联系人' },
  { key: 'contact_phone', header: '电话' },
  { key: 'is_active', header: '状态', render: r => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
];

export default function SupplierList() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', tier: 'approved', contact_name: '', contact_phone: '', contact_email: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['suppliers', search, tierFilter],
    queryFn: () => scmApi.listSuppliers({ search: search || undefined, tier: tierFilter || undefined }),
  });

  return (
    <div className="p-6">
      <PageHeader
        title="供应商管理"
        subtitle="Suppliers"
        icon={<Truck className="text-orange-500" size={24} />}
        actionLabel="新建供应商"
        onAction={() => setShowCreate(true)}
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(215.4,16.3%,46.9%)]" />
            <input
              type="text" placeholder="搜索..." value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 pr-3 py-2 border rounded-lg text-sm w-48 focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]"
            />
          </div>
          <select
            value={tierFilter} onChange={e => setTierFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]"
          >
            <option value="">全部等级</option>
            <option value="strategic">战略级</option>
            <option value="preferred">优选级</option>
            <option value="approved">合格级</option>
            <option value="blacklisted">黑名单</option>
          </select>
        </div>
      </PageHeader>
      <DataTable<Supplier>
        columns={columns}
        data={data || []}
        loading={isLoading}
      />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建供应商" onSubmit={async () => {
        await scmApi.createSupplier(form);
        qc.invalidateQueries({ queryKey: ['suppliers'] });
        setForm({ code: '', name: '', tier: 'approved', contact_name: '', contact_phone: '', contact_email: '' });
      }}>
        <FormField label="供应商编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="供应商名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="等级">
          <FormSelect value={form.tier} onChange={e => setForm(f => ({ ...f, tier: e.target.value }))}>
            <option value="approved">合格级</option>
            <option value="preferred">优选级</option>
            <option value="strategic">战略级</option>
          </FormSelect>
        </FormField>
        <FormField label="联系人"><FormInput value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} /></FormField>
        <FormField label="电话"><FormInput value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} /></FormField>
        <FormField label="邮箱"><FormInput type="email" value={form.contact_email} onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
