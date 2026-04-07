import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { plmApi, api, type Customer } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const columns: Column<Customer>[] = [
  { key: 'code', header: '客户编码', className: 'font-mono' },
  { key: 'name', header: '客户名称' },
  { key: 'rating', header: '评级', render: r => <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.rating === 'A' ? 'bg-green-100 text-green-700' : r.rating === 'B' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>{r.rating}级</span> },
  { key: 'is_online', header: '线上', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return <span className={`text-xs ${rec.is_online ? 'text-green-600' : 'text-gray-400'}`}>{rec.is_online ? '是' : '否'}</span>;
  }},
  { key: 'contact_name', header: '联系人', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const contacts = rec.contacts as Array<{ name?: string }> | undefined;
    return contacts?.[0]?.name || '—';
  }},
  { key: 'contact_phone', header: '电话', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const contacts = rec.contacts as Array<{ phone?: string }> | undefined;
    return contacts?.[0]?.phone || '—';
  }},
];

export default function CustomerList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', kind: 'b2b', rating: 'B', contact_name: '', contact_phone: '' });
  const { data, isLoading } = useQuery({ queryKey: ['customers'], queryFn: plmApi.listCustomers });

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="客户管理" subtitle="Customer 360" icon={<Users size={22} strokeWidth={1.5} />} actionLabel="新建客户" onAction={() => setShowCreate(true)} />
      <DataTable<Customer> columns={columns} data={data || []} loading={isLoading} />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建客户" onSubmit={async () => {
        // Create customer (only fields the API accepts)
        const cust = await plmApi.createCustomer({ code: form.code, name: form.name, kind: form.kind as 'b2b', rating: form.rating });
        // Create contact separately if provided
        if (form.contact_name && cust.id) {
          await api.post(`/plm/customers/${cust.id}/contacts`, { name: form.contact_name, phone: form.contact_phone || undefined });
        }
        qc.invalidateQueries({ queryKey: ['customers'] });
        setForm({ code: '', name: '', kind: 'b2b', rating: 'B', contact_name: '', contact_phone: '' });
      }}>
        <FormField label="客户编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="客户名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="类型">
          <FormSelect value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value }))}>
            <option value="b2b">企业客户 (B2B)</option>
            <option value="b2c">个人客户 (B2C)</option>
          </FormSelect>
        </FormField>
        <FormField label="评级"><FormSelect value={form.rating} onChange={e => setForm(f => ({ ...f, rating: e.target.value }))}><option value="A">A级</option><option value="B">B级</option><option value="C">C级</option></FormSelect></FormField>
        <FormField label="联系人"><FormInput value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} /></FormField>
        <FormField label="电话"><FormInput value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
