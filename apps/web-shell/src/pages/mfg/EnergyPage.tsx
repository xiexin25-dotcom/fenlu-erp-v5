import { useQuery } from '@tanstack/react-query';
import { Zap } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

interface EnergyMeter { id: string; code: string; name: string; meter_type: string; location: string; }

const columns: Column<EnergyMeter>[] = [
  { key: 'code', header: '表计编码', className: 'font-mono' },
  { key: 'name', header: '表计名称' },
  { key: 'meter_type', header: '类型' },
  { key: 'location', header: '安装位置' },
];

export default function EnergyPage() {
  const { data, isLoading } = useQuery({ queryKey: ['energy-meters'], queryFn: () => api.get<EnergyMeter[]>('/mfg/energy/meters') });
  return (
    <div className="p-6">
      <PageHeader title="能耗监控" subtitle="Energy Meters + Unit Consumption" icon={<Zap className="text-amber-500" size={24} />} />
      <DataTable<EnergyMeter> columns={columns} data={data || []} loading={isLoading} emptyText="暂无能耗表计" />
    </div>
  );
}
