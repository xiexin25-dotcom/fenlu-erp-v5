import { useQuery } from '@tanstack/react-query';
import { Banknote } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

interface Payroll { id: string; period: string; status: string; total_amount: unknown; head_count: number; }

function fmt(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const columns: Column<Payroll>[] = [
  { key: 'period', header: '期间' },
  { key: 'head_count', header: '人数', className: 'text-right' },
  { key: 'total_amount', header: '总金额', className: 'text-right', render: r => fmt(r.total_amount) },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function PayrollList() {
  const { data, isLoading } = useQuery({ queryKey: ['payroll'], queryFn: () => api.get<Payroll[]>('/mgmt/hr/payroll') });
  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="薪资管理" subtitle="月度工资条" icon={<Banknote size={22} strokeWidth={1.5} />} />
      <DataTable<Payroll> columns={columns} data={data || []} loading={isLoading} emptyText="暂无工资条" />
    </div>
  );
}
