import { useQuery } from '@tanstack/react-query';
import { ClipboardCheck } from 'lucide-react';
import { mfgApi, type QCInspection } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<QCInspection>[] = [
  { key: 'work_order_id', header: '工单', render: r => r.work_order_id?.slice(0, 8), className: 'font-mono' },
  { key: 'inspector', header: '检验员' },
  { key: 'sample_size', header: '抽样数', className: 'text-right' },
  { key: 'defect_count', header: '缺陷数', className: 'text-right', render: r => <span className={r.defect_count > 0 ? 'text-red-600 font-medium' : ''}>{r.defect_count}</span> },
  { key: 'result', header: '结果', render: r => <StatusBadge status={r.result} /> },
  { key: 'notes', header: '备注', className: 'max-w-48 truncate' },
  { key: 'created_at', header: '时间', render: r => new Date(r.created_at).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }) },
];

export default function QCInspectionList() {
  const { data, isLoading } = useQuery({ queryKey: ['qc-inspections'], queryFn: () => mfgApi.listInspections() });
  return (
    <div className="p-6">
      <PageHeader title="质量检验" subtitle="QC Inspections" icon={<ClipboardCheck className="text-green-500" size={24} />} />
      <DataTable<QCInspection> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
