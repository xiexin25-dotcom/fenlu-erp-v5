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
  { key: 'workshop_id', header: '车间', render: () => '默认车间' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'is_special_equipment', header: '特种设备', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return rec.is_special_equipment ? <span className="text-orange-600 text-xs font-medium">是</span> : <span className="text-gray-400 text-xs">否</span>;
  }},
];

export default function EquipmentList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '' });
  const { data, isLoading } = useQuery({ queryKey: ['equipment'], queryFn: mfgApi.listEquipment });

  return (
    <div className="p-6">
      <PageHeader title="设备管理" subtitle="EAM + OEE" icon={<Wrench className="text-green-500" size={24} />} actionLabel="新建设备" onAction={() => setShowCreate(true)} />
      <DataTable<Equipment> columns={columns} data={data || []} loading={isLoading} />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建设备" onSubmit={async () => { await mfgApi.createEquipment(form); qc.invalidateQueries({ queryKey: ['equipment'] }); }}>
        <FormField label="设备编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="设备名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
      </FormDialog>
    </div>
  );
}
