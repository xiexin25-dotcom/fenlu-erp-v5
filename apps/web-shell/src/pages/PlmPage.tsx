import { Package } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import ModuleCard from '@/components/ModuleCard';

const modules = [
  { title: '产品主数据', desc: 'Product + BOM + Routing', path: '/plm/products' },
  { title: 'ECN 工程变更', desc: '变更审批流程', path: '/plm/ecn' },
  { title: 'CRM 客户管理', desc: 'Customer 360', path: '/plm/customers' },
  { title: '商机漏斗', desc: 'Lead → Opportunity → Order', path: '/plm/crm-funnel' },
  { title: '售后工单', desc: 'SLA + NPS', path: '/plm/service-tickets' },
];

export default function PlmPage() {
  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="产品生命周期管理" subtitle="Product Lifecycle Management" icon={<Package size={22} strokeWidth={1.5} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(m => <ModuleCard key={m.title} {...m} />)}
      </div>
    </div>
  );
}
