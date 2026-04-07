import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { mfgApi, type SafetyHazard } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<SafetyHazard>[] = [
  { key: 'title', header: '隐患标题' },
  { key: 'severity', header: '严重性', render: r => <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${r.severity === 'critical' ? 'bg-red-100 text-red-700' : r.severity === 'major' ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'}`}>{r.severity === 'critical' ? '严重' : r.severity === 'major' ? '重大' : '一般'}</span> },
  { key: 'location', header: '位置' },
  { key: 'reporter', header: '报告人' },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'created_at', header: '报告时间', render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
];

export default function SafetyHazardList() {
  const [statusFilter, setStatusFilter] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['safety-hazards', statusFilter],
    queryFn: () => mfgApi.listHazards(statusFilter || undefined),
  });

  return (
    <div className="p-6">
      <PageHeader title="安全生产" subtitle="隐患闭环管理" icon={<AlertTriangle className="text-red-500" size={24} />}>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
          <option value="">全部状态</option>
          <option value="REPORTED">已报告</option>
          <option value="ASSIGNED">已分配</option>
          <option value="RECTIFYING">整改中</option>
          <option value="VERIFIED">已验证</option>
          <option value="CLOSED">已关闭</option>
        </select>
      </PageHeader>
      <DataTable<SafetyHazard> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
