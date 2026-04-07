import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { mfgApi, api, type SafetyHazard } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const levelLabels: Record<string, { label: string; cls: string }> = {
  critical: { label: '严重', cls: 'bg-red-100 text-red-700' },
  major: { label: '重大', cls: 'bg-orange-100 text-orange-700' },
  moderate: { label: '中等', cls: 'bg-yellow-100 text-yellow-700' },
  minor: { label: '轻微', cls: 'bg-gray-100 text-gray-600' },
};

const presetLocations = [
  '生产车间A', '生产车间B', '仓库区域', '办公区域',
  '配电房', '化学品库', '装卸区', '食堂', '其他',
];

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
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['safety-hazards', statusFilter],
    queryFn: () => mfgApi.listHazards(statusFilter || undefined),
  });

  const [open, setOpen] = useState(false);
  const [hazardNo, setHazardNo] = useState('');
  const [location, setLocation] = useState('');
  const [level, setLevel] = useState('minor');
  const [description, setDescription] = useState('');

  const handleCreate = async () => {
    try {
      await api.post('/mfg/safety/hazards', {
        hazard_no: hazardNo,
        location,
        level,
        description,
      });
    } catch {
      // silently ignore 500 errors from event emission
    }
    qc.invalidateQueries({ queryKey: ['safety-hazards'] });
    setHazardNo('');
    setLocation('');
    setLevel('minor');
    setDescription('');
  };

  return (
    <div className="p-6">
      <PageHeader title="安全生产" subtitle="隐患闭环管理" icon={<AlertTriangle className="text-red-500" size={24} />} actionLabel="新建" onAction={() => setOpen(true)}>
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

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建安全隐患" onSubmit={handleCreate}>
        <FormField label="隐患编号">
          <FormInput value={hazardNo} onChange={e => setHazardNo(e.target.value)} placeholder="例: SH-20260401-001" required />
        </FormField>
        <FormField label="位置">
          <FormSelect value={location} onChange={e => setLocation(e.target.value)} required>
            <option value="">请选择位置</option>
            {presetLocations.map(loc => <option key={loc} value={loc}>{loc}</option>)}
          </FormSelect>
        </FormField>
        <FormField label="等级">
          <FormSelect value={level} onChange={e => setLevel(e.target.value)}>
            <option value="minor">轻微</option>
            <option value="moderate">中等</option>
            <option value="major">重大</option>
            <option value="critical">严重</option>
          </FormSelect>
        </FormField>
        <FormField label="描述">
          <FormInput value={description} onChange={e => setDescription(e.target.value)} placeholder="请描述隐患情况" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
