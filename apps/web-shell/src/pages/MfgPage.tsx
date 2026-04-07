import { useNavigate } from 'react-router-dom';
import { Factory } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

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
  const navigate = useNavigate();
  return (
    <div className="p-6">
      <PageHeader title="生产制造管理" icon={<Factory className="text-green-500" size={24} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(item => (
          <div key={item.title} onClick={() => navigate(item.path)}
            className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] cursor-pointer hover:shadow-md hover:border-green-300 transition">
            <h3 className="font-medium">{item.title}</h3>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
