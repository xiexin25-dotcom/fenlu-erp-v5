import { useQuery } from '@tanstack/react-query';
import { Package } from 'lucide-react';
import { scmApi, type InventoryItem } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

const columns: Column<InventoryItem>[] = [
  { key: 'product_name', header: '产品', render: r => r.product_name || r.product_id?.slice(0, 8) },
  { key: 'warehouse_name', header: '仓库', render: r => r.warehouse_name || r.warehouse_id?.slice(0, 8) },
  { key: 'batch_no', header: '批次号', className: 'font-mono' },
  { key: 'quantity', header: '数量', className: 'text-right font-medium', render: r => r.quantity.toLocaleString() },
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
