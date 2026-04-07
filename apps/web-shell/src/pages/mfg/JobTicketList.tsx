import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Clipboard } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import FormDialog, { FormField, FormInput } from '@/components/FormDialog';

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
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['job-tickets'], queryFn: () => api.get<JobTicket[]>('/mfg/job-tickets') });

  const [open, setOpen] = useState(false);
  const [workOrderId, setWorkOrderId] = useState('');
  const [ticketNo, setTicketNo] = useState('');

  const handleCreate = async () => {
    await api.post('/mfg/job-tickets', {
      work_order_id: workOrderId,
      ticket_no: ticketNo,
    });
    qc.invalidateQueries({ queryKey: ['job-tickets'] });
    setWorkOrderId('');
    setTicketNo('');
  };

  return (
    <div className="p-6">
      <PageHeader
        title="工序报工"
        subtitle="Job Tickets"
        icon={<Clipboard className="text-green-500" size={24} />}
        actionLabel="新建"
        onAction={() => setOpen(true)}
      />
      <DataTable<JobTicket> columns={columns} data={data || []} loading={isLoading} emptyText="暂无报工记录" />

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建报工" onSubmit={handleCreate}>
        <FormField label="工单ID">
          <FormInput value={workOrderId} onChange={e => setWorkOrderId(e.target.value)} placeholder="工单UUID" required />
        </FormField>
        <FormField label="报工单号">
          <FormInput value={ticketNo} onChange={e => setTicketNo(e.target.value)} placeholder="例: JT-20260401-001" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
