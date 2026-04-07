import { useQuery } from '@tanstack/react-query';
import { Package } from 'lucide-react';
import { scmApi, type InventoryItem } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

function num(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 });
}

const columns: Column<InventoryItem>[] = [
  { key: 'product_id', header: '产品', render: r => (r.product_id || '').slice(0, 8), className: 'font-mono' },
  { key: 'warehouse_id', header: '仓库', render: r => (r.warehouse_id || '').slice(0, 8), className: 'font-mono' },
  { key: 'batch_no', header: '批次号', className: 'font-mono' },
  { key: 'on_hand', header: '在手数量', className: 'text-right font-medium', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return num(rec.on_hand);
  }},
  { key: 'reserved', header: '预留数量', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return num(rec.reserved);
  }},
  { key: 'available', header: '可用数量', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return num(rec.available);
  }},
];

export default function InventoryList() {
  const { data, isLoading } = useQuery({ queryKey: ['inventory'], queryFn: () => scmApi.listInventory() });
  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="库存管理" subtitle="StockMove 全追溯" icon={<Package size={22} strokeWidth={1.5} />} />
      <DataTable<InventoryItem> columns={columns} data={data || []} loading={isLoading} emptyText="暂无库存记录" />
    </div>
  );
}
