import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Wrench } from 'lucide-react';
import { mfgApi, type Equipment } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput } from '@/components/FormDialog';

const columns: Column<Equipment>[] = [
  { key: 'code', header: '设备编码', className: 'font-mono' },
  { key: 'name', header: '设备名称' },
  { key: 'equipment_type', header: '类型' },
  { key: 'location', header: '位置' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'last_maintenance', header: '上次保养', render: r => r.last_maintenance ? new Date(r.last_maintenance).toLocaleDateString('zh-CN') : '—' },
];

export default function EquipmentList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', equipment_type: '', location: '' });
  const { data, isLoading } = useQuery({ queryKey: ['equipment'], queryFn: mfgApi.listEquipment });

  return (
    <div className="p-6">
      <PageHeader title="设备管理" subtitle="EAM + OEE" icon={<Wrench className="text-green-500" size={24} />} actionLabel="新建设备" onAction={() => setShowCreate(true)} />
      <DataTable<Equipment> columns={columns} data={data || []} loading={isLoading} />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建设备" onSubmit={async () => { await mfgApi.createEquipment(form); qc.invalidateQueries({ queryKey: ['equipment'] }); }}>
        <FormField label="设备编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="设备名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="类型"><FormInput value={form.equipment_type} onChange={e => setForm(f => ({ ...f, equipment_type: e.target.value }))} /></FormField>
        <FormField label="位置"><FormInput value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
