import { useQuery } from '@tanstack/react-query';
import { Package } from 'lucide-react';
import { scmApi, type InventoryItem } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

const columns: Column<InventoryItem>[] = [
  { key: 'product_id', header: '产品', render: r => (r.product_id || '').slice(0, 8), className: 'font-mono' },
  { key: 'warehouse_id', header: '仓库', render: r => (r.warehouse_id || '').slice(0, 8), className: 'font-mono' },
  { key: 'batch_no', header: '批次号', className: 'font-mono' },
  { key: 'on_hand', header: '在手数量', className: 'text-right font-medium', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.on_hand as number) ?? 0).toLocaleString();
  }},
  { key: 'reserved', header: '预留数量', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.reserved as number) ?? 0).toLocaleString();
  }},
  { key: 'available', header: '可用数量', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.available as number) ?? 0).toLocaleString();
  }},
];

export default function InventoryList() {
  const { data, isLoading } = useQuery({ queryKey: ['inventory'], queryFn: () => scmApi.listInventory() });
  return (
    <div className="p-6">
      <PageHeader title="库存管理" subtitle="StockMove 全追溯" icon={<Package className="text-orange-500" size={24} />} />
      <DataTable<InventoryItem> columns={columns} data={data || []} loading={isLoading} emptyText="暂无库存记录" />
    </div>
  );
}
