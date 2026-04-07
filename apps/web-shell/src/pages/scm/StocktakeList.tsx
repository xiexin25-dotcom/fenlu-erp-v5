import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardList } from 'lucide-react';
import { scmApi, type Stocktake } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

export default function StocktakeList() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['stocktakes'], queryFn: scmApi.listStocktakes });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses-all'], queryFn: scmApi.listWarehouses });

  const whMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const w of warehouses || []) m[w.id] = w.name || w.code;
    return m;
  }, [warehouses]);

  const columns: Column<Stocktake>[] = [
    { key: 'stocktake_no', header: '盘点单号', className: 'font-mono', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return (rec.stocktake_no as string) || '—';
    }},
    { key: 'warehouse_id', header: '仓库', render: r => whMap[r.warehouse_id] || (r.warehouse_id || '').slice(0, 8) },
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
    { key: 'stocktake_date', header: '盘点日期', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      const val = rec.stocktake_date as string | undefined;
      return val ? new Date(val).toLocaleDateString('zh-CN') : '—';
    }},
  ];

  const [open, setOpen] = useState(false);
  const [stocktakeNo, setStocktakeNo] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [productId, setProductId] = useState('');
  const [actualQty, setActualQty] = useState('');

  const handleCreate = async () => {
    await scmApi.createStocktake({
      stocktake_no: stocktakeNo,
      warehouse_id: warehouseId,
      lines: [
        {
          product_id: productId,
          actual_quantity: Number(actualQty) || 0,
        },
      ],
    } as unknown as Partial<Stocktake>);
    qc.invalidateQueries({ queryKey: ['stocktakes'] });
    setStocktakeNo('');
    setWarehouseId('');
    setProductId('');
    setActualQty('');
  };

  return (
    <div className="p-6">
      <PageHeader
        title="盘点管理"
        subtitle="差异自动调整"
        icon={<ClipboardList className="text-orange-500" size={24} />}
        actionLabel="新建"
        onAction={() => setOpen(true)}
      />
      <DataTable<Stocktake> columns={columns} data={data || []} loading={isLoading} />

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建盘点" onSubmit={handleCreate}>
        <FormField label="盘点单号">
          <FormInput value={stocktakeNo} onChange={e => setStocktakeNo(e.target.value)} placeholder="例: ST-20260401-001" required />
        </FormField>
        <FormField label="仓库">
          <FormSelect value={warehouseId} onChange={e => setWarehouseId(e.target.value)} required>
            <option value="">请选择仓库</option>
            {(warehouses || []).map(w => <option key={w.id} value={w.id}>{w.name || w.code}</option>)}
          </FormSelect>
        </FormField>
        <div style={{ borderTop: '1px solid var(--divider)', paddingTop: '12px', marginTop: '4px' }}>
          <p className="text-[13px] font-medium mb-3" style={{ color: 'var(--fg-secondary)' }}>盘点明细</p>
        </div>
        <FormField label="产品ID">
          <FormInput value={productId} onChange={e => setProductId(e.target.value)} placeholder="产品UUID" required />
        </FormField>
        <FormField label="实际数量">
          <FormInput type="number" value={actualQty} onChange={e => setActualQty(e.target.value)} placeholder="0" min="0" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
