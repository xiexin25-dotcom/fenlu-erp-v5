import { useQuery } from '@tanstack/react-query';
import { Calendar } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

interface Workstation { id: string; code: string; name: string; capacity_per_hour: number; is_active: boolean; }

const columns: Column<Workstation>[] = [
  { key: 'code', header: '工位编码', className: 'font-mono' },
  { key: 'name', header: '工位名称' },
  { key: 'capacity_per_hour', header: '产能(件/时)', className: 'text-right' },
  { key: 'is_active', header: '状态', render: r => <span className={`text-xs font-medium ${r.is_active ? 'text-green-600' : 'text-gray-400'}`}>{r.is_active ? '启用' : '停用'}</span> },
];

export default function APSPage() {
  const { data, isLoading } = useQuery({ queryKey: ['workstations'], queryFn: () => api.get<Workstation[]>('/mfg/aps/workstations') });
  return (
    <div className="p-6">
      <PageHeader title="APS 排产" subtitle="工位管理 + FIFO 排程" icon={<Calendar className="text-green-500" size={24} />} />
      <DataTable<Workstation> columns={columns} data={data || []} loading={isLoading} emptyText="暂无工位数据" />
    </div>
  );
}
