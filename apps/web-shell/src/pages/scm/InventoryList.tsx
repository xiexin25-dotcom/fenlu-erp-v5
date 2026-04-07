import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Package } from 'lucide-react';
import { scmApi, plmApi, type InventoryItem } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

function num(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return Math.round(n || 0).toLocaleString();
}

function tenantId() { return localStorage.getItem('tenant_id') || ''; }

export default function InventoryList() {
  const { data, isLoading } = useQuery({ queryKey: ['inventory'], queryFn: () => scmApi.listInventory() });
  const { data: prodData } = useQuery({ queryKey: ['products-all'], queryFn: () => plmApi.listProducts(0, 100) });
  const { data: whData } = useQuery({ queryKey: ['warehouses-all'], queryFn: () => scmApi.listWarehouses() });

  const prodMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const p of prodData?.items || []) m[p.id] = `${p.name} (${p.code})`;
    return m;
  }, [prodData]);

  const whMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const w of whData || []) m[w.id] = w.name || w.code;
    return m;
  }, [whData]);

  const columns: Column<InventoryItem>[] = [
    { key: 'product', header: '产品', render: r => prodMap[r.product_id] || r.product_id?.slice(0, 8) },
    { key: 'warehouse', header: '仓库', render: r => whMap[r.warehouse_id] || r.warehouse_id?.slice(0, 8) },
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
      const v = typeof rec.available === 'string' ? parseFloat(rec.available as string) : (rec.available as number) || 0;
      return <span style={{ color: v > 0 ? 'var(--status-green-fg)' : 'var(--fg-tertiary)' }}>{Math.round(v).toLocaleString()}</span>;
    }},
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="库存管理" subtitle="StockMove 全追溯" icon={<Package size={22} strokeWidth={1.5} />} />
      <DataTable<InventoryItem> columns={columns} data={data || []} loading={isLoading} emptyText="暂无库存记录" />
    </div>
  );
}
