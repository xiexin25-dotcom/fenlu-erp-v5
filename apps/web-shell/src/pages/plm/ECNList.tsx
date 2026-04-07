import { useQuery } from '@tanstack/react-query';
import { GitBranch } from 'lucide-react';
import { api, type ECN } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<ECN>[] = [
  { key: 'ecn_no', header: 'ECN 编号', className: 'font-mono', render: r => (r as unknown as Record<string, string>).ecn_no || '' },
  { key: 'title', header: '变更标题' },
  { key: 'description', header: '描述', className: 'max-w-64 truncate' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'created_at', header: '创建时间', render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
];

export default function ECNList() {
  const { data, isLoading } = useQuery({
    queryKey: ['ecn-list'],
    queryFn: () => api.get<ECN[]>('/plm/ecn'),
  });

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="ECN 工程变更" subtitle="Engineering Change Notice" icon={<GitBranch size={22} strokeWidth={1.5} />} />
      <DataTable<ECN> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
