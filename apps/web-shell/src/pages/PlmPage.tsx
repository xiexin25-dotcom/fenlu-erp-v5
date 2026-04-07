import { Package } from 'lucide-react';

export default function PlmPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Package className="text-blue-500" size={24} />
        <h1 className="text-xl font-bold">产品生命周期管理</h1>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { title: '产品主数据', desc: 'Product + BOM + Routing', count: '—' },
          { title: 'CAD 文件管理', desc: 'MinIO 存储', count: '—' },
          { title: 'ECN 工程变更', desc: '变更审批流程', count: '—' },
          { title: 'CRM 客户管理', desc: 'Customer 360', count: '—' },
          { title: '商机漏斗', desc: 'Lead → Opportunity → Order', count: '—' },
          { title: '售后工单', desc: 'SLA + NPS', count: '—' },
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
