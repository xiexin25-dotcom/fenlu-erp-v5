import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ShieldCheck, CheckCircle, XCircle, Clock, Send } from 'lucide-react';
import { mgmtApi, api, type ApprovalInstance } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

interface ApprovalDef { id: string; business_type: string; name: string; steps_config: Array<{ step_no: number; name: string }> }

const typeLabels: Record<string, string> = {
  purchase_order: '采购审批', tier_change: '供应商等级变更',
  leave_request: '请假审批', expense_claim: '费用报销',
};

const statusColors: Record<string, string> = {
  pending: 'var(--status-amber-fg)', approved: 'var(--status-green-fg)',
  rejected: 'var(--status-red-fg)', withdrawn: 'var(--fg-tertiary)',
};

function ApprovalActions({ instance, onAction }: { instance: ApprovalInstance; onAction: (id: string, action: string) => void }) {
  if (instance.status !== 'pending') return null;
  return (
    <div className="flex gap-2">
      <button onClick={e => { e.stopPropagation(); onAction(instance.id, 'approve'); }}
        className="flex items-center gap-1 px-2 py-1 text-xs rounded" style={{ background: 'var(--status-green)', color: 'var(--status-green-fg)' }}>
        <CheckCircle size={12} /> 同意
      </button>
      <button onClick={e => { e.stopPropagation(); onAction(instance.id, 'reject'); }}
        className="flex items-center gap-1 px-2 py-1 text-xs rounded" style={{ background: 'var(--status-red)', color: 'var(--status-red-fg)' }}>
        <XCircle size={12} /> 驳回
      </button>
    </div>
  );
}

export default function ApprovalList() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'pending' | 'all' | 'submit'>('pending');
  const [showSubmit, setShowSubmit] = useState(false);
  const [form, setForm] = useState({ business_type: '', reason: '' });

  const { data: pending, isLoading: pendingLoading } = useQuery({
    queryKey: ['approvals-pending'],
    queryFn: () => mgmtApi.listPendingApprovals(),
  });
  const { data: all, isLoading: allLoading } = useQuery({
    queryKey: ['approvals-all'],
    queryFn: () => mgmtApi.listApprovals(),
  });
  const { data: defs } = useQuery({
    queryKey: ['approval-defs'],
    queryFn: () => api.get<ApprovalDef[]>('/mgmt/approval/definitions'),
  });
  const { data: empData } = useQuery({
    queryKey: ['employees-all'],
    queryFn: () => api.get<Array<{ id: string; name: string; employee_no: string }>>('/mgmt/hr/employees'),
  });

  const defMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const d of defs || []) m[d.business_type] = d.name;
    return m;
  }, [defs]);

  const empMap = useMemo(() => {
    const m: Record<string, string> = {};
    const empItems = Array.isArray(empData) ? empData : (empData as unknown as { items?: Array<{ id: string; name: string; employee_no: string }> })?.items || [];
    for (const e of empItems) m[e.id] = `${e.name} (${e.employee_no})`;
    return m;
  }, [empData]);

  const handleAction = async (id: string, action: string) => {
    await api.post(`/mgmt/approval/${id}/action`, { action, comment: action === 'approve' ? '同意' : '不同意' });
    qc.invalidateQueries({ queryKey: ['approvals-pending'] });
    qc.invalidateQueries({ queryKey: ['approvals-all'] });
  };

  const columns: Column<ApprovalInstance>[] = [
    { key: 'type', header: '审批类型', render: r => {
      const rec = r as unknown as Record<string, string>;
      return defMap[r.business_type] || typeLabels[r.business_type] || r.business_type;
    }},
    { key: 'business_id', header: '业务单号', className: 'font-mono', render: r => r.business_id?.slice(0, 8) },
    { key: 'progress', header: '进度', render: r => {
      const pct = r.total_steps > 0 ? Math.round((r.current_step / r.total_steps) * 100) : 0;
      return (
        <div className="flex items-center gap-2">
          <div className="w-16 h-[5px] rounded-full overflow-hidden" style={{ background: 'var(--divider)' }}>
            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'var(--status-green-fg)' }} />
          </div>
          <span className="text-[11px]" style={{ color: 'var(--fg-tertiary)' }}>{r.current_step}/{r.total_steps}</span>
        </div>
      );
    }},
    { key: 'initiator', header: '发起人', render: r => {
      const rec = r as unknown as Record<string, string>;
      const iid = rec.initiator_id || '';
      return empMap[iid] || iid.slice(0, 8);
    }},
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
    { key: 'action', header: '操作', render: r => <ApprovalActions instance={r} onAction={handleAction} /> },
  ];

  const pendingList = pending || [];
  const allList = all || [];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="审批中心" subtitle="Approval Flow" icon={<ShieldCheck size={22} strokeWidth={1.5} />}
        actionLabel="发起审批" onAction={() => setShowSubmit(true)} />

      {/* Tab bar */}
      <div className="flex gap-1 mb-5 p-1 rounded w-fit" style={{ background: 'var(--bg-hover)' }}>
        <button onClick={() => setTab('pending')} className={`flex items-center gap-1.5 px-4 py-1.5 text-[13px] rounded transition ${tab === 'pending' ? 'bg-white shadow font-medium' : ''}`}>
          <Clock size={14} /> 待我审批
          {pendingList.length > 0 && <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full" style={{ background: 'var(--status-red)', color: 'var(--status-red-fg)' }}>{pendingList.length}</span>}
        </button>
        <button onClick={() => setTab('all')} className={`flex items-center gap-1.5 px-4 py-1.5 text-[13px] rounded transition ${tab === 'all' ? 'bg-white shadow font-medium' : ''}`}>
          <Send size={14} /> 全部记录
        </button>
      </div>

      {tab === 'pending' ? (
        <DataTable<ApprovalInstance> columns={columns} data={pendingList} loading={pendingLoading} emptyText="暂无待审批事项" />
      ) : (
        <DataTable<ApprovalInstance> columns={columns} data={allList} loading={allLoading} emptyText="暂无审批记录" />
      )}

      {/* Submit new approval */}
      <FormDialog open={showSubmit} onClose={() => setShowSubmit(false)} title="发起审批" onSubmit={async () => {
        await api.post('/mgmt/approval', {
          business_type: form.business_type,
          business_id: crypto.randomUUID(),
          payload: { reason: form.reason },
        });
        qc.invalidateQueries({ queryKey: ['approvals-all'] });
        qc.invalidateQueries({ queryKey: ['approvals-pending'] });
        setForm({ business_type: '', reason: '' });
      }} submitLabel="提交审批">
        <FormField label="审批类型">
          <FormSelect value={form.business_type} onChange={e => setForm(f => ({ ...f, business_type: e.target.value }))} required>
            <option value="">选择类型</option>
            {(defs || []).map(d => <option key={d.id} value={d.business_type}>{d.name} ({d.steps_config.length}步审批)</option>)}
          </FormSelect>
        </FormField>
        <FormField label="申请理由">
          <FormInput value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} placeholder="请填写申请理由" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
