import { useQuery } from '@tanstack/react-query';
import { Headphones } from 'lucide-react';
import { plmApi, type ServiceTicket } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<ServiceTicket>[] = [
  { key: 'ticket_number', header: '工单号', className: 'font-mono' },
  { key: 'subject', header: '主题' },
  { key: 'customer_name', header: '客户', render: r => r.customer_name || r.customer_id?.slice(0, 8) },
  { key: 'priority', header: '优先级', render: r => <span className={`text-xs font-medium ${r.priority === 'high' ? 'text-red-600' : r.priority === 'medium' ? 'text-amber-600' : 'text-gray-600'}`}>{r.priority === 'high' ? '高' : r.priority === 'medium' ? '中' : '低'}</span> },
  { key: 'sla_hours', header: 'SLA', render: r => `${r.sla_hours}h` },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'nps_score', header: 'NPS', render: r => r.nps_score !== null ? <span className={r.nps_score >= 8 ? 'text-green-600' : r.nps_score >= 6 ? 'text-amber-600' : 'text-red-600'}>{r.nps_score}</span> : '—' },
];

export default function ServiceTicketList() {
  const { data, isLoading } = useQuery({ queryKey: ['service-tickets'], queryFn: plmApi.listTickets });
  return (
    <div className="p-6">
      <PageHeader title="售后工单" subtitle="Service Tickets · SLA + NPS" icon={<Headphones className="text-blue-500" size={24} />} />
      <DataTable<ServiceTicket> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
