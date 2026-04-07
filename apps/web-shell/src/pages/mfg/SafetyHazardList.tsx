import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { mfgApi, type SafetyHazard } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const levelLabels: Record<string, { label: string; cls: string }> = {
  critical: { label: '严重', cls: 'bg-red-100 text-red-700' },
  major: { label: '重大', cls: 'bg-orange-100 text-orange-700' },
  moderate: { label: '中等', cls: 'bg-yellow-100 text-yellow-700' },
  minor: { label: '轻微', cls: 'bg-gray-100 text-gray-600' },
};

const columns: Column<SafetyHazard>[] = [
  { key: 'hazard_no', header: '隐患编号', className: 'font-mono', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.hazard_no as string) || '—';
  }},
  { key: 'level', header: '等级', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const level = (rec.level as string) || '';
    const info = levelLabels[level] || { label: level, cls: 'bg-gray-100 text-gray-600' };
    return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${info.cls}`}>{info.label}</span>;
  }},
  { key: 'location', header: '位置', render: r => r.location || '—' },
  { key: 'reported_by', header: '报告人', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.reported_by as string) || '—';
  }},
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  { key: 'rectified_at', header: '整改时间', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.rectified_at as string | undefined;
    return val ? new Date(val).toLocaleDateString('zh-CN') : '—';
  }},
  { key: 'closed_at', header: '关闭时间', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.closed_at as string | undefined;
    return val ? new Date(val).toLocaleDateString('zh-CN') : '—';
  }},
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
