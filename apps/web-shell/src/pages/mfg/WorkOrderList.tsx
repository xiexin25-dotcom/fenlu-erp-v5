import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Factory } from 'lucide-react';
import { mfgApi, plmApi, type WorkOrder } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

// Extract numeric value from quantity (could be number or {value, uom} object)
function qty(v: unknown): number {
  if (typeof v === 'number') return v;
  if (v && typeof v === 'object' && 'value' in v) return Number((v as { value: string | number }).value) || 0;
  return Number(v) || 0;
}

export default function WorkOrderList() {
  const { data: woData, isLoading } = useQuery({ queryKey: ['work-orders'], queryFn: mfgApi.listWorkOrders });
  const { data: prodData } = useQuery({ queryKey: ['products-all'], queryFn: () => plmApi.listProducts(0, 100) });

  // Build product name map
  const prodMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const p of prodData?.items || []) {
      m[p.id] = `${p.name} (${p.code})`;
    }
    return m;
  }, [prodData]);

  const woList = (woData || []) as WorkOrder[];

  const columns: Column<WorkOrder>[] = [
    { key: 'order_no', header: '工单号', className: 'font-mono',
      render: r => (r as unknown as Record<string, string>).order_no || '' },
    { key: 'product', header: '产品',
      render: r => prodMap[r.product_id] || r.product_id?.slice(0, 8) },
    { key: 'planned_qty', header: '计划数', className: 'w-24 text-right',
      render: r => qty(r.planned_quantity).toLocaleString() },
    { key: 'completed_qty', header: '完成数', className: 'w-24 text-right',
      render: r => qty(r.completed_quantity).toLocaleString() },
    { key: 'progress', header: '进度', className: 'w-32', render: r => {
      const planned = qty(r.planned_quantity);
      const completed = qty(r.completed_quantity);
      const pct = planned > 0 ? Math.round((completed / planned) * 100) : 0;
      return (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-[5px] rounded-full overflow-hidden" style={{ background: 'var(--divider)' }}>
            <div className="h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%`, background: 'var(--status-green-fg)' }} />
          </div>
          <span className="text-[11px] w-8 text-right" style={{ color: 'var(--fg-tertiary)' }}>{pct}%</span>
        </div>
      );
    }},
    { key: 'planned_start', header: '计划开始',
      render: r => r.planned_start ? new Date(r.planned_start).toLocaleDateString('zh-CN') : '' },
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader
        title="生产工单"
        subtitle="Work Orders"
        icon={<Factory size={22} strokeWidth={1.5} />}
      />
      <DataTable<WorkOrder>
        columns={columns}
        data={woList}
        loading={isLoading}
      />
    </div>
  );
}
