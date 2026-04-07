import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Headphones } from 'lucide-react';
import { plmApi, api, type ServiceTicket } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const statusLabels: Record<string, string> = {
  open: '待处理', in_progress: '处理中', pending_customer: '等待客户',
  resolved: '已解决', closed: '已关闭',
};

export default function ServiceTicketList() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['service-tickets'], queryFn: () => api.get<ServiceTicket[]>('/plm/service/tickets') });
  const { data: custs } = useQuery({ queryKey: ['customers-all'], queryFn: plmApi.listCustomers });

  const [open, setOpen] = useState(false);
  const [customerId, setCustomerId] = useState('');
  const [ticketNo, setTicketNo] = useState('');
  const [description, setDescription] = useState('');

  const custMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const c of custs || []) m[c.id] = c.name;
    return m;
  }, [custs]);

  const columns: Column<ServiceTicket>[] = [
    { key: 'ticket_no', header: '工单号', className: 'font-mono',
      render: r => (r as unknown as Record<string, string>).ticket_no || '' },
    { key: 'description', header: '问题描述',
      render: r => (r as unknown as Record<string, string>).description || '' },
    { key: 'customer', header: '客户',
      render: r => custMap[r.customer_id] || r.customer_id?.slice(0, 8) },
    { key: 'sla_due', header: 'SLA截止',
      render: r => {
        const due = (r as unknown as Record<string, string>).sla_due_at;
        if (!due) return '—';
        return new Date(due).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      }},
    { key: 'status', header: '状态',
      render: r => <StatusBadge status={r.status} /> },
    { key: 'nps_score', header: 'NPS',
      render: r => r.nps_score !== null && r.nps_score !== undefined
        ? <span style={{ color: r.nps_score >= 8 ? 'var(--status-green-fg)' : r.nps_score >= 6 ? 'var(--status-amber-fg)' : 'var(--status-red-fg)', fontWeight: 600 }}>{r.nps_score}</span>
        : <span style={{ color: 'var(--fg-tertiary)' }}>—</span> },
  ];

  const handleCreate = async () => {
    await api.post('/plm/service/tickets', {
      customer_id: customerId,
      ticket_no: ticketNo,
      description,
    });
    qc.invalidateQueries({ queryKey: ['service-tickets'] });
    setCustomerId('');
    setTicketNo('');
    setDescription('');
  };

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader
        title="售后工单"
        subtitle="Service Tickets · SLA + NPS"
        icon={<Headphones size={22} strokeWidth={1.5} />}
        actionLabel="新建"
        onAction={() => setOpen(true)}
      />
      <DataTable<ServiceTicket> columns={columns} data={data || []} loading={isLoading} />

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建售后工单" onSubmit={handleCreate}>
        <FormField label="客户">
          <FormSelect value={customerId} onChange={e => setCustomerId(e.target.value)} required>
            <option value="">请选择客户</option>
            {(custs || []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </FormSelect>
        </FormField>
        <FormField label="工单号">
          <FormInput value={ticketNo} onChange={e => setTicketNo(e.target.value)} placeholder="例: ST-20260401-001" required />
        </FormField>
        <FormField label="问题描述">
          <FormInput value={description} onChange={e => setDescription(e.target.value)} placeholder="请描述问题" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
