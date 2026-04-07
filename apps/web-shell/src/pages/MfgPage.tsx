import { Factory } from 'lucide-react';

export default function MfgPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Factory className="text-green-500" size={24} />
        <h1 className="text-xl font-bold">生产制造管理</h1>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { title: '生产工单', desc: 'MES 生产管控' },
          { title: '工序报工', desc: 'Job Ticket 报工' },
          { title: '质量检验', desc: 'QC / SPC 控制图' },
          { title: '设备管理', desc: 'EAM + OEE' },
          { title: '安全生产', desc: '隐患闭环管理' },
          { title: '能耗监控', desc: '单耗分析' },
          { title: 'APS 排产', desc: 'FIFO + 产能' },
        ].map(item => (
          <div key={item.title} className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] hover:shadow-md transition cursor-pointer">
            <h3 className="font-medium">{item.title}</h3>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
