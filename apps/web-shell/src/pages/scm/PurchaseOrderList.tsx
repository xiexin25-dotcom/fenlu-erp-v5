import { useQuery } from '@tanstack/react-query';
import { ShoppingCart } from 'lucide-react';
import { scmApi, type PurchaseOrder } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<PurchaseOrder>[] = [
  { key: 'order_no', header: '采购单号', className: 'font-mono', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.order_no as string) || '—';
  }},
  { key: 'supplier_id', header: '供应商', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.supplier_id as string) || '').slice(0, 8);
  }, className: 'font-mono' },
  { key: 'total_amount', header: '金额', className: 'text-right', render: r => r.total_amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'currency', header: '币种', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.currency as string) || 'CNY';
  }},
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function PurchaseOrderList() {
  const { data, isLoading } = useQuery({ queryKey: ['purchase-orders'], queryFn: scmApi.listPOs });
  return (
    <div className="p-6">
      <PageHeader title="采购管理" subtitle="PR → RFQ → PO → Receipt" icon={<ShoppingCart className="text-orange-500" size={24} />} />
      <DataTable<PurchaseOrder> columns={columns} data={data || []} loading={isLoading} emptyText="暂无采购单" />
    </div>
  );
}
