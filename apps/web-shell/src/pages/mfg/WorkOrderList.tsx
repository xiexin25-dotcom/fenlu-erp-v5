import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Factory } from 'lucide-react';
import { mfgApi, type WorkOrder } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput } from '@/components/FormDialog';

const statusFlow: Record<string, string> = {
  PLANNED: 'RELEASED', RELEASED: 'IN_PROGRESS', IN_PROGRESS: 'COMPLETED', COMPLETED: 'CLOSED',
};

function StatusAction({ wo, onTransition }: { wo: WorkOrder; onTransition: (id: string, s: string) => void }) {
  const next = statusFlow[wo.status];
  if (!next) return null;
  const labels: Record<string, string> = {
    RELEASED: '下达', IN_PROGRESS: '开工', COMPLETED: '完工', CLOSED: '关闭',
  };
  return (
    <button
      onClick={e => { e.stopPropagation(); onTransition(wo.id, next); }}
      className="px-2 py-1 text-xs bg-[hsl(221.2,83.2%,53.3%)] text-white rounded hover:opacity-90 transition"
    >{labels[next]}</button>
  );
}

export default function WorkOrderList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ order_number: '', product_name: '', planned_quantity: '100' });

  const { data, isLoading } = useQuery({ queryKey: ['work-orders'], queryFn: mfgApi.listWorkOrders });

  const handleTransition = async (id: string, status: string) => {
    await mfgApi.transitionStatus(id, status);
    qc.invalidateQueries({ queryKey: ['work-orders'] });
  };

  const columns: Column<WorkOrder>[] = [
    { key: 'order_number', header: '工单号', className: 'font-mono' },
    { key: 'product_name', header: '产品', render: r => r.product_name || r.product_id?.slice(0, 8) },
    { key: 'planned_quantity', header: '计划数', className: 'w-20 text-right' },
    { key: 'completed_quantity', header: '完成数', className: 'w-20 text-right' },
    { key: 'progress', header: '进度', className: 'w-32', render: r => {
      const pct = r.planned_quantity > 0 ? Math.round((r.completed_quantity / r.planned_quantity) * 100) : 0;
      return (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-[hsl(210,40%,96.1%)] rounded-full overflow-hidden">
            <div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
          </div>
          <span className="text-xs w-8 text-right">{pct}%</span>
        </div>
      );
    }},
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
    { key: 'action', header: '操作', render: r => <StatusAction wo={r} onTransition={handleTransition} /> },
  ];

  return (
    <div className="p-6">
      <PageHeader
        title="生产工单"
        subtitle="Work Orders"
        icon={<Factory className="text-green-500" size={24} />}
        actionLabel="新建工单"
        onAction={() => setShowCreate(true)}
      />
      <DataTable<WorkOrder>
        columns={columns}
        data={data || []}
        loading={isLoading}
      />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建工单" onSubmit={async () => {
        await mfgApi.createWorkOrder({
          order_number: form.order_number,
          planned_quantity: Number(form.planned_quantity),
        });
        qc.invalidateQueries({ queryKey: ['work-orders'] });
        setForm({ order_number: '', product_name: '', planned_quantity: '100' });
      }}>
        <FormField label="工单号"><FormInput value={form.order_number} onChange={e => setForm(f => ({ ...f, order_number: e.target.value }))} required /></FormField>
        <FormField label="计划数量"><FormInput type="number" value={form.planned_quantity} onChange={e => setForm(f => ({ ...f, planned_quantity: e.target.value }))} required /></FormField>
      </FormDialog>
    </div>
  );
}
