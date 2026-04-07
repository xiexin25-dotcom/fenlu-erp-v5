import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Warehouse } from 'lucide-react';
import { scmApi, type Warehouse as WarehouseType } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput } from '@/components/FormDialog';

const columns: Column<WarehouseType>[] = [
  { key: 'code', header: '仓库编码', className: 'font-mono' },
  { key: 'name', header: '仓库名称' },
  { key: 'address', header: '地址' },
  { key: 'is_active', header: '状态', render: r => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
];

export default function WarehouseList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', address: '' });
  const { data, isLoading } = useQuery({ queryKey: ['warehouses'], queryFn: scmApi.listWarehouses });

  return (
    <div className="p-6">
      <PageHeader title="仓库管理" subtitle="多仓 + 4级库位" icon={<Warehouse className="text-orange-500" size={24} />} actionLabel="新建仓库" onAction={() => setShowCreate(true)} />
      <DataTable<WarehouseType> columns={columns} data={data || []} loading={isLoading} />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建仓库" onSubmit={async () => { await scmApi.createWarehouse(form); qc.invalidateQueries({ queryKey: ['warehouses'] }); }}>
        <FormField label="仓库编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="仓库名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="地址"><FormInput value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
