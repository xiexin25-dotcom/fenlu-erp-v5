import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Package } from 'lucide-react';
import { scmApi, plmApi, type InventoryItem } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

function num(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return Math.round(n || 0).toLocaleString();
}

export default function InventoryList() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['inventory'], queryFn: () => scmApi.listInventory() });
  const { data: prodData } = useQuery({ queryKey: ['products-all'], queryFn: () => plmApi.listProducts(0, 100) });
  const { data: whData } = useQuery({ queryKey: ['warehouses-all'], queryFn: () => scmApi.listWarehouses() });

  const [open, setOpen] = useState(false);
  const [productId, setProductId] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [batchNo, setBatchNo] = useState('');

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

  const handleCreate = async () => {
    await scmApi.receive({
      product_id: productId,
      warehouse_id: warehouseId,
      quantity: Number(quantity) || 0,
      batch_no: batchNo,
    });
    qc.invalidateQueries({ queryKey: ['inventory'] });
    setProductId('');
    setWarehouseId('');
    setQuantity('');
    setBatchNo('');
  };

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader
        title="库存管理"
        subtitle="StockMove 全追溯"
        icon={<Package size={22} strokeWidth={1.5} />}
        actionLabel="入库"
        onAction={() => setOpen(true)}
      />
      <DataTable<InventoryItem> columns={columns} data={data || []} loading={isLoading} emptyText="暂无库存记录" />

      <FormDialog open={open} onClose={() => setOpen(false)} title="入库操作" onSubmit={handleCreate} submitLabel="确认入库">
        <FormField label="产品">
          <FormSelect value={productId} onChange={e => setProductId(e.target.value)} required>
            <option value="">请选择产品</option>
            {(prodData?.items || []).map(p => <option key={p.id} value={p.id}>{p.name} ({p.code})</option>)}
          </FormSelect>
        </FormField>
        <FormField label="仓库">
          <FormSelect value={warehouseId} onChange={e => setWarehouseId(e.target.value)} required>
            <option value="">请选择仓库</option>
            {(whData || []).map(w => <option key={w.id} value={w.id}>{w.name || w.code}</option>)}
          </FormSelect>
        </FormField>
        <FormField label="数量">
          <FormInput type="number" value={quantity} onChange={e => setQuantity(e.target.value)} placeholder="0" min="1" required />
        </FormField>
        <FormField label="批次号">
          <FormInput value={batchNo} onChange={e => setBatchNo(e.target.value)} placeholder="例: BATCH-20260401" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
