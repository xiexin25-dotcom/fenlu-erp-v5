import { Factory } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import ModuleCard from '@/components/ModuleCard';

const modules = [
  { title: '生产工单', desc: 'MES 生产管控', path: '/mfg/work-orders' },
  { title: '工序报工', desc: 'Job Ticket 报工', path: '/mfg/job-tickets' },
  { title: '质量检验', desc: 'QC / SPC 控制图', path: '/mfg/qc' },
  { title: '设备管理', desc: 'EAM + OEE', path: '/mfg/equipment' },
  { title: '安全生产', desc: '隐患闭环管理', path: '/mfg/safety' },
  { title: '能耗监控', desc: '单耗分析', path: '/mfg/energy' },
  { title: 'APS 排产', desc: 'FIFO + 产能', path: '/mfg/aps' },
];

export default function MfgPage() {
  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="生产制造管理" subtitle="Manufacturing Execution" icon={<Factory size={22} strokeWidth={1.5} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(m => <ModuleCard key={m.title} {...m} />)}
      </div>
    </div>
  );
}
