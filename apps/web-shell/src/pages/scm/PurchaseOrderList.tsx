import { useQuery } from '@tanstack/react-query';
import { ShoppingCart } from 'lucide-react';
import { scmApi, type PurchaseOrder } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<PurchaseOrder>[] = [
  { key: 'po_number', header: '采购单号', className: 'font-mono' },
  { key: 'supplier_name', header: '供应商', render: r => r.supplier_name || r.supplier_id?.slice(0, 8) },
  { key: 'total_amount', header: '金额', className: 'text-right', render: r => r.total_amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'created_at', header: '创建时间', render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
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
