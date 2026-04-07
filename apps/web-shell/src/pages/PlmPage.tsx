import { useNavigate } from 'react-router-dom';
import { Package } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

const modules = [
  { title: '产品主数据', desc: 'Product + BOM + Routing', path: '/plm/products' },
  { title: 'CAD 文件管理', desc: 'MinIO 存储', path: '' },
  { title: 'ECN 工程变更', desc: '变更审批流程', path: '' },
  { title: 'CRM 客户管理', desc: 'Customer 360', path: '/plm/customers' },
  { title: '商机漏斗', desc: 'Lead → Opportunity → Order', path: '' },
  { title: '售后工单', desc: 'SLA + NPS', path: '/plm/service-tickets' },
];

export default function PlmPage() {
  const navigate = useNavigate();
  return (
    <div className="p-6">
      <PageHeader title="产品生命周期管理" icon={<Package className="text-blue-500" size={24} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(item => (
          <div key={item.title} onClick={() => item.path && navigate(item.path)}
            className={`bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] transition ${item.path ? 'cursor-pointer hover:shadow-md hover:border-blue-300' : 'opacity-60'}`}>
            <h3 className="font-medium">{item.title}</h3>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">{item.desc}</p>
            {!item.path && <span className="text-xs text-[hsl(215.4,16.3%,46.9%)] mt-2 inline-block">即将上线</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
