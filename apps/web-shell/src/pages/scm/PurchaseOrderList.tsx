import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ShoppingCart } from 'lucide-react';
import { scmApi, type PurchaseOrder } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

function fmt(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const columns: Column<PurchaseOrder>[] = [
  { key: 'order_no', header: '采购单号', className: 'font-mono', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.order_no as string) || '—';
  }},
  { key: 'supplier_id', header: '供应商', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.supplier_id as string) || '').slice(0, 8);
  }, className: 'font-mono' },
  { key: 'total_amount', header: '金额', className: 'text-right', render: r => fmt(r.total_amount) },
  { key: 'currency', header: '币种', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.currency as string) || 'CNY';
  }},
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function PurchaseOrderList() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['purchase-orders'], queryFn: scmApi.listPOs });
  const { data: suppliers } = useQuery({ queryKey: ['suppliers-all'], queryFn: () => scmApi.listSuppliers() });

  const [open, setOpen] = useState(false);
  const [orderNo, setOrderNo] = useState('');
  const [supplierId, setSupplierId] = useState('');
  const [productId, setProductId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');

  const handleCreate = async () => {
    await scmApi.createPO({
      order_no: orderNo,
      supplier_id: supplierId,
      lines: [
        {
          product_id: productId,
          quantity: Number(quantity) || 0,
          unit_price: Number(unitPrice) || 0,
        },
      ],
    });
    qc.invalidateQueries({ queryKey: ['purchase-orders'] });
    setOrderNo('');
    setSupplierId('');
    setProductId('');
    setQuantity('');
    setUnitPrice('');
  };

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader
        title="采购管理"
        subtitle="PR → RFQ → PO → Receipt"
        icon={<ShoppingCart size={22} strokeWidth={1.5} />}
        actionLabel="新建"
        onAction={() => setOpen(true)}
      />
      <DataTable<PurchaseOrder> columns={columns} data={data || []} loading={isLoading} emptyText="暂无采购单" />

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建采购单" onSubmit={handleCreate}>
        <FormField label="采购单号">
          <FormInput value={orderNo} onChange={e => setOrderNo(e.target.value)} placeholder="例: PO-20260401-001" required />
        </FormField>
        <FormField label="供应商">
          <FormSelect value={supplierId} onChange={e => setSupplierId(e.target.value)} required>
            <option value="">请选择供应商</option>
            {(suppliers || []).map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
          </FormSelect>
        </FormField>
        <div style={{ borderTop: '1px solid var(--divider)', paddingTop: '12px', marginTop: '4px' }}>
          <p className="text-[13px] font-medium mb-3" style={{ color: 'var(--fg-secondary)' }}>采购明细</p>
        </div>
        <FormField label="产品ID">
          <FormInput value={productId} onChange={e => setProductId(e.target.value)} placeholder="产品UUID" required />
        </FormField>
        <FormField label="数量">
          <FormInput type="number" value={quantity} onChange={e => setQuantity(e.target.value)} placeholder="0" min="1" required />
        </FormField>
        <FormField label="单价">
          <FormInput type="number" value={unitPrice} onChange={e => setUnitPrice(e.target.value)} placeholder="0.00" min="0" step="0.01" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
