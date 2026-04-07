import { Truck } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import ModuleCard from '@/components/ModuleCard';

const modules = [
  { title: '供应商管理', desc: '评级 + Tier 转换', path: '/scm/suppliers' },
  { title: '采购管理', desc: 'PR → RFQ → PO → Receipt', path: '/scm/purchase-orders' },
  { title: '仓库管理', desc: '多仓 + 4级库位', path: '/scm/warehouses' },
  { title: '库存管理', desc: 'StockMove 全追溯', path: '/scm/inventory' },
  { title: '盘点管理', desc: '差异自动调整', path: '/scm/stocktakes' },
];

export default function ScmPage() {
  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="供应链管理" subtitle="Supply Chain Management" icon={<Truck size={22} strokeWidth={1.5} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(m => <ModuleCard key={m.title} {...m} />)}
      </div>
    </div>
  );
}
