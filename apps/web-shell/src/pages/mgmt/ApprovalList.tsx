import { useQuery } from '@tanstack/react-query';
import { ShieldCheck } from 'lucide-react';
import { mgmtApi, type ApprovalInstance } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<ApprovalInstance>[] = [
  { key: 'business_type', header: '业务类型' },
  { key: 'business_id', header: '业务ID', className: 'font-mono', render: r => r.business_id?.slice(0, 8) },
  { key: 'progress', header: '进度', render: r => `${r.current_step}/${r.total_steps}` },
  { key: 'initiator_id', header: '发起人', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return ((rec.initiator_id as string) || '').slice(0, 8);
  }, className: 'font-mono' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function ApprovalList() {
  const { data, isLoading } = useQuery({ queryKey: ['approvals'], queryFn: () => mgmtApi.listApprovals() });
  return (
    <div className="p-6">
      <PageHeader title="审批中心" subtitle="Approval Flow" icon={<ShieldCheck className="text-indigo-500" size={24} />} />
      <DataTable<ApprovalInstance> columns={columns} data={data || []} loading={isLoading} emptyText="暂无审批记录" />
    </div>
  );
}
