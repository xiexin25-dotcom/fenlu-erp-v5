import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { mgmtApi, type Employee } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput } from '@/components/FormDialog';

const columns: Column<Employee>[] = [
  { key: 'employee_no', header: '工号', className: 'font-mono' },
  { key: 'name', header: '姓名' },
  { key: 'department', header: '部门' },
  { key: 'position', header: '职位' },
  { key: 'hire_date', header: '入职日期', render: r => r.hire_date?.slice(0, 10) },
  { key: 'is_active', header: '状态', render: r => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
];

export default function EmployeeList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ employee_no: '', name: '', department: '', position: '', hire_date: '' });
  const { data, isLoading } = useQuery({ queryKey: ['employees'], queryFn: mgmtApi.listEmployees });

  return (
    <div className="p-6">
      <PageHeader title="员工管理" subtitle="花名册" icon={<Users className="text-indigo-500" size={24} />} actionLabel="新建员工" onAction={() => setShowCreate(true)} />
      <DataTable<Employee> columns={columns} data={data || []} loading={isLoading} />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建员工" onSubmit={async () => { await mgmtApi.createEmployee(form); qc.invalidateQueries({ queryKey: ['employees'] }); }}>
        <FormField label="工号"><FormInput value={form.employee_no} onChange={e => setForm(f => ({ ...f, employee_no: e.target.value }))} required /></FormField>
        <FormField label="姓名"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="部门"><FormInput value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))} /></FormField>
        <FormField label="职位"><FormInput value={form.position} onChange={e => setForm(f => ({ ...f, position: e.target.value }))} /></FormField>
        <FormField label="入职日期"><FormInput type="date" value={form.hire_date} onChange={e => setForm(f => ({ ...f, hire_date: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
