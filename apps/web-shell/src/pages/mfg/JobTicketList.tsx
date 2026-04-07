import { useQuery } from '@tanstack/react-query';
import { Clipboard } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

interface JobTicket {
  id: string; work_order_id: string; operation_name?: string;
  completed_qty: number; scrap_qty: number; minutes: number;
  worker: string; created_at: string;
}

const columns: Column<JobTicket>[] = [
  { key: 'work_order_id', header: '工单', render: r => r.work_order_id?.slice(0, 8), className: 'font-mono' },
  { key: 'operation_name', header: '工序', render: r => r.operation_name || '—' },
  { key: 'worker', header: '操作员' },
  { key: 'completed_qty', header: '完成数', className: 'text-right' },
  { key: 'scrap_qty', header: '报废数', className: 'text-right', render: r => <span className={r.scrap_qty > 0 ? 'text-red-600' : ''}>{r.scrap_qty}</span> },
  { key: 'minutes', header: '工时(min)', className: 'text-right' },
  { key: 'created_at', header: '报工时间', render: r => new Date(r.created_at).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }) },
];

export default function JobTicketList() {
  const { data, isLoading } = useQuery({ queryKey: ['job-tickets'], queryFn: () => api.get<JobTicket[]>('/mfg/job-tickets') });
  return (
    <div className="p-6">
      <PageHeader title="工序报工" subtitle="Job Tickets" icon={<Clipboard className="text-green-500" size={24} />} />
      <DataTable<JobTicket> columns={columns} data={data || []} loading={isLoading} emptyText="暂无报工记录" />
    </div>
  );
}
