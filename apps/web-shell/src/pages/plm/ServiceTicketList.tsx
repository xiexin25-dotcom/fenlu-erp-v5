import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Headphones } from 'lucide-react';
import { plmApi, api, type ServiceTicket } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const flowLabels: Record<string, { next: string; label: string }> = {
  open: { next: 'in_progress', label: '开始处理' },
  in_progress: { next: 'resolved', label: '标记解决' },
  resolved: { next: 'close', label: '关闭(NPS)' },
};

function TicketActions({ ticket, onTransition, onClose }: {
  ticket: ServiceTicket;
  onTransition: (id: string, status: string) => void;
  onClose: (id: string) => void;
}) {
  const flow = flowLabels[ticket.status];
  if (!flow) return null;
  const colors: Record<string, string> = {
    '开始处理': 'var(--accent)',
    '标记解决': 'var(--status-green-fg)',
    '关闭(NPS)': 'var(--status-purple-fg)',
  };
  return (
    <button
      onClick={e => {
        e.stopPropagation();
        if (flow.next === 'close') onClose(ticket.id);
        else onTransition(ticket.id, flow.next);
      }}
      className="px-2 py-1 text-xs rounded text-white"
      style={{ background: colors[flow.label] || 'var(--accent)' }}
    >{flow.label}</button>
  );
}

export default function ServiceTicketList() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['service-tickets'], queryFn: () => api.get<ServiceTicket[]>('/plm/service/tickets') });
  const { data: custs } = useQuery({ queryKey: ['customers-all'], queryFn: plmApi.listCustomers });

  const [showCreate, setShowCreate] = useState(false);
  const [customerId, setCustomerId] = useState('');
  const [ticketNo, setTicketNo] = useState('');
  const [description, setDescription] = useState('');

  const [showClose, setShowClose] = useState(false);
  const [closeId, setCloseId] = useState('');
  const [npsScore, setNpsScore] = useState('8');

  const custMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const c of custs || []) m[c.id] = c.name;
    return m;
  }, [custs]);

  const handleTransition = async (id: string, status: string) => {
    await api.post(`/plm/service/tickets/${id}/transition`, { target_status: status });
    qc.invalidateQueries({ queryKey: ['service-tickets'] });
  };

  const handleClose = (id: string) => {
    setCloseId(id);
    setShowClose(true);
  };

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
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
    { key: 'nps_score', header: 'NPS',
      render: r => r.nps_score !== null && r.nps_score !== undefined
        ? <span style={{ color: r.nps_score >= 8 ? 'var(--status-green-fg)' : r.nps_score >= 6 ? 'var(--status-amber-fg)' : 'var(--status-red-fg)', fontWeight: 600 }}>{r.nps_score}</span>
        : <span style={{ color: 'var(--fg-tertiary)' }}>—</span> },
    { key: 'action', header: '操作', render: r => <TicketActions ticket={r} onTransition={handleTransition} onClose={handleClose} /> },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="售后工单" subtitle="Service Tickets · SLA + NPS" icon={<Headphones size={22} strokeWidth={1.5} />}
        actionLabel="新建" onAction={() => setShowCreate(true)} />
      <DataTable<ServiceTicket> columns={columns} data={data || []} loading={isLoading} />

      {/* 新建 */}
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建售后工单" onSubmit={async () => {
        await api.post('/plm/service/tickets', { customer_id: customerId, ticket_no: ticketNo, description });
        qc.invalidateQueries({ queryKey: ['service-tickets'] });
        setCustomerId(''); setTicketNo(''); setDescription('');
      }}>
        <FormField label="客户">
          <FormSelect value={customerId} onChange={e => setCustomerId(e.target.value)} required>
            <option value="">请选择客户</option>
            {(custs || []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </FormSelect>
        </FormField>
        <FormField label="工单号"><FormInput value={ticketNo} onChange={e => setTicketNo(e.target.value)} placeholder="如 SVC-20260401" required /></FormField>
        <FormField label="问题描述"><FormInput value={description} onChange={e => setDescription(e.target.value)} placeholder="请描述问题" required /></FormField>
      </FormDialog>

      {/* 关闭+NPS */}
      <FormDialog open={showClose} onClose={() => setShowClose(false)} title="关闭工单 — 客户满意度评分" onSubmit={async () => {
        await api.post(`/plm/service/tickets/${closeId}/close`, { nps_score: Number(npsScore) });
        qc.invalidateQueries({ queryKey: ['service-tickets'] });
        setCloseId(''); setNpsScore('8');
      }} submitLabel="确认关闭">
        <FormField label="NPS 评分 (0-10)">
          <FormSelect value={npsScore} onChange={e => setNpsScore(e.target.value)}>
            {[10,9,8,7,6,5,4,3,2,1,0].map(n => (
              <option key={n} value={String(n)}>{n} — {n >= 9 ? '非常满意' : n >= 7 ? '满意' : n >= 5 ? '一般' : '不满意'}</option>
            ))}
          </FormSelect>
        </FormField>
      </FormDialog>
    </div>
  );
}
