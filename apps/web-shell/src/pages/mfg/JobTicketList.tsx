import { useQuery } from '@tanstack/react-query';
import { Clipboard } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

interface JobTicket {
  id: string; work_order_id: string; ticket_no: string;
  completed_qty: number; scrap_qty: number; minutes: number;
  reported_at: string; remark: string;
}

const columns: Column<JobTicket>[] = [
  { key: 'ticket_no', header: '报工单号', className: 'font-mono' },
  { key: 'work_order_id', header: '工单', render: r => r.work_order_id?.slice(0, 8), className: 'font-mono' },
  { key: 'completed_qty', header: '完成数', className: 'text-right' },
  { key: 'scrap_qty', header: '报废数', className: 'text-right', render: r => <span className={r.scrap_qty > 0 ? 'text-red-600' : ''}>{r.scrap_qty}</span> },
  { key: 'minutes', header: '工时(min)', className: 'text-right' },
  { key: 'remark', header: '备注', render: r => r.remark || '—' },
  { key: 'reported_at', header: '报工时间', render: r => r.reported_at ? new Date(r.reported_at).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }) : '—' },
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
