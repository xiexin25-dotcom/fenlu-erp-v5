import { useQuery } from '@tanstack/react-query';
import { Banknote } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

interface Payroll { id: string; period: string; status: string; total_amount: number; head_count: number; }

const columns: Column<Payroll>[] = [
  { key: 'period', header: '期间' },
  { key: 'head_count', header: '人数', className: 'text-right' },
  { key: 'total_amount', header: '总金额', className: 'text-right', render: r => r.total_amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function PayrollList() {
  const { data, isLoading } = useQuery({ queryKey: ['payroll'], queryFn: () => api.get<Payroll[]>('/mgmt/hr/payroll') });
  return (
    <div className="p-6">
      <PageHeader title="薪资管理" subtitle="月度工资条" icon={<Banknote className="text-indigo-500" size={24} />} />
      <DataTable<Payroll> columns={columns} data={data || []} loading={isLoading} emptyText="暂无工资条，使用 /mgmt/hr/payroll/run 生成" />
    </div>
  );
}
