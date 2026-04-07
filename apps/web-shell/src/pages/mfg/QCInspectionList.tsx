import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardCheck } from 'lucide-react';
import { mfgApi, api, plmApi, type QCInspection } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const columns: Column<QCInspection>[] = [
  { key: 'inspection_no', header: '检验单号', className: 'font-mono', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.inspection_no as string) || '—';
  }},
  { key: 'type', header: '类型', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.type as string) || '—';
  }},
  { key: 'work_order_id', header: '工单', render: r => r.work_order_id?.slice(0, 8), className: 'font-mono' },
  { key: 'product_id', header: '产品', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.product_id as string) || '').slice(0, 8);
  }, className: 'font-mono' },
  { key: 'inspector_id', header: '检验员', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.inspector_id as string) || '').slice(0, 8);
  }, className: 'font-mono' },
  { key: 'sample_size', header: '抽样数', className: 'text-right' },
  { key: 'defect_count', header: '缺陷数', className: 'text-right', render: r => <span className={r.defect_count > 0 ? 'text-red-600 font-medium' : ''}>{r.defect_count}</span> },
  { key: 'result', header: '结果', render: r => <StatusBadge status={r.result} /> },
];

export default function QCInspectionList() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['qc-inspections'], queryFn: () => mfgApi.listInspections() });
  const { data: prodData } = useQuery({ queryKey: ['products-all'], queryFn: () => plmApi.listProducts(0, 100) });

  const [open, setOpen] = useState(false);
  const [inspectionNo, setInspectionNo] = useState('');
  const [type, setType] = useState('iqc');
  const [productId, setProductId] = useState('');
  const [sampleSize, setSampleSize] = useState('');
  const [defectCount, setDefectCount] = useState('');
  const [result, setResult] = useState('pass');

  const handleCreate = async () => {
    const inspectorId = localStorage.getItem('user_id') || '00000000-0000-0000-0000-000000000001';
    // Use first product if none selected
    const pid = productId || (prodData?.items?.[0]?.id || '');
    await api.post('/mfg/qc/inspections', {
      inspection_no: inspectionNo,
      type,
      product_id: pid,
      inspector_id: inspectorId,
      sample_size: Number(sampleSize) || 0,
      defect_count: Number(defectCount) || 0,
      result,
    });
    qc.invalidateQueries({ queryKey: ['qc-inspections'] });
    setInspectionNo('');
    setType('iqc');
    setProductId('');
    setSampleSize('');
    setDefectCount('');
    setResult('pass');
  };

  return (
    <div className="p-6">
      <PageHeader
        title="质量检验"
        subtitle="QC Inspections"
        icon={<ClipboardCheck className="text-green-500" size={24} />}
        actionLabel="新建"
        onAction={() => setOpen(true)}
      />
      <DataTable<QCInspection> columns={columns} data={data || []} loading={isLoading} />

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建质检记录" onSubmit={handleCreate}>
        <FormField label="检验单号">
          <FormInput value={inspectionNo} onChange={e => setInspectionNo(e.target.value)} placeholder="例: IQC-20260401-001" required />
        </FormField>
        <FormField label="检验类型">
          <FormSelect value={type} onChange={e => setType(e.target.value)}>
            <option value="iqc">IQC (来料检验)</option>
            <option value="ipqc">IPQC (过程检验)</option>
            <option value="oqc">OQC (出货检验)</option>
            <option value="fai">FAI (首件检验)</option>
          </FormSelect>
        </FormField>
        <FormField label="产品">
          <FormSelect value={productId} onChange={e => setProductId(e.target.value)}>
            <option value="">请选择产品</option>
            {(prodData?.items || []).map(p => <option key={p.id} value={p.id}>{p.name} ({p.code})</option>)}
          </FormSelect>
        </FormField>
        <FormField label="抽样数量">
          <FormInput type="number" value={sampleSize} onChange={e => setSampleSize(e.target.value)} placeholder="0" min="0" required />
        </FormField>
        <FormField label="缺陷数量">
          <FormInput type="number" value={defectCount} onChange={e => setDefectCount(e.target.value)} placeholder="0" min="0" required />
        </FormField>
        <FormField label="检验结果">
          <FormSelect value={result} onChange={e => setResult(e.target.value)}>
            <option value="pass">通过 (Pass)</option>
            <option value="conditional">有条件通过 (Conditional)</option>
          </FormSelect>
        </FormField>
      </FormDialog>
    </div>
  );
}
