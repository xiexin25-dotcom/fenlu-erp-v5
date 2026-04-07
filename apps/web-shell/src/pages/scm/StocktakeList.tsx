import { useQuery } from '@tanstack/react-query';
import { ClipboardList } from 'lucide-react';
import { scmApi, type Stocktake } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<Stocktake>[] = [
  { key: 'stocktake_number', header: '盘点单号', className: 'font-mono' },
  { key: 'warehouse_name', header: '仓库', render: r => r.warehouse_name || r.warehouse_id?.slice(0, 8) },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'created_at', header: '创建时间', render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
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
