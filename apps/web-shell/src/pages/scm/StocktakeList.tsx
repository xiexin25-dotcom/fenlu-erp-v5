import { useQuery } from '@tanstack/react-query';
import { ClipboardList } from 'lucide-react';
import { scmApi, type Stocktake } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<Stocktake>[] = [
  { key: 'stocktake_no', header: '盘点单号', className: 'font-mono', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.stocktake_no as string) || '—';
  }},
  { key: 'warehouse_id', header: '仓库', render: r => (r.warehouse_id || '').slice(0, 8), className: 'font-mono' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'stocktake_date', header: '盘点日期', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.stocktake_date as string | undefined;
    return val ? new Date(val).toLocaleDateString('zh-CN') : '—';
  }},
];

export default function StocktakeList() {
  const { data, isLoading } = useQuery({ queryKey: ['stocktakes'], queryFn: scmApi.listStocktakes });
  return (
    <div className="p-6">
      <PageHeader title="盘点管理" subtitle="差异自动调整" icon={<ClipboardList className="text-orange-500" size={24} />} />
      <DataTable<Stocktake> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
