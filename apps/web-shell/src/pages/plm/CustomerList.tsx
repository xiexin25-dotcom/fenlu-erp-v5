import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { plmApi, type Customer } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const columns: Column<Customer>[] = [
  { key: 'code', header: '客户编码', className: 'font-mono' },
  { key: 'name', header: '客户名称' },
  { key: 'rating', header: '评级', render: r => <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.rating === 'A' ? 'bg-green-100 text-green-700' : r.rating === 'B' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>{r.rating}级</span> },
  { key: 'industry', header: '行业' },
  { key: 'contact_name', header: '联系人' },
  { key: 'contact_phone', header: '电话' },
];

export default function CustomerList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', rating: 'B', industry: '', contact_name: '', contact_phone: '' });
  const { data, isLoading } = useQuery({ queryKey: ['customers'], queryFn: plmApi.listCustomers });

  return (
    <div className="p-6">
      <PageHeader title="客户管理" subtitle="Customer 360" icon={<Users className="text-blue-500" size={24} />} actionLabel="新建客户" onAction={() => setShowCreate(true)} />
      <DataTable<Customer> columns={columns} data={data || []} loading={isLoading} />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建客户" onSubmit={async () => { await plmApi.createCustomer(form); qc.invalidateQueries({ queryKey: ['customers'] }); }}>
        <FormField label="客户编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="客户名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="评级"><FormSelect value={form.rating} onChange={e => setForm(f => ({ ...f, rating: e.target.value }))}><option value="A">A级</option><option value="B">B级</option><option value="C">C级</option></FormSelect></FormField>
        <FormField label="行业"><FormInput value={form.industry} onChange={e => setForm(f => ({ ...f, industry: e.target.value }))} /></FormField>
        <FormField label="联系人"><FormInput value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} /></FormField>
        <FormField label="电话"><FormInput value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
