import { useQuery } from '@tanstack/react-query';
import { GitBranch } from 'lucide-react';
import { plmApi, type ECN } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<ECN>[] = [
  { key: 'ecn_number', header: 'ECN 编号', className: 'font-mono' },
  { key: 'title', header: '变更标题' },
  { key: 'description', header: '描述', className: 'max-w-64 truncate' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'created_at', header: '创建时间', render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
];

export default function ECNList() {
  // ECN doesn't have a list endpoint, so we show an empty state for now
  return (
    <div className="p-6">
      <PageHeader title="ECN 工程变更" subtitle="Engineering Change Notice" icon={<GitBranch className="text-blue-500" size={24} />} />
      <DataTable<ECN> columns={columns} data={[]} loading={false} emptyText="暂无工程变更记录，请通过 API 创建" />
    </div>
  );
}
