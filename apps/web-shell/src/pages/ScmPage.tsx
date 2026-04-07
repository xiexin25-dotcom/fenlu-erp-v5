import { useNavigate } from 'react-router-dom';
import { Truck } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

const modules = [
  { title: '供应商管理', desc: '评级 + Tier 转换', path: '/scm/suppliers' },
  { title: '采购管理', desc: 'PR→RFQ→PO→Receipt', path: '' },
  { title: '仓库管理', desc: '多仓 + 4级库位', path: '' },
  { title: '库存管理', desc: 'StockMove 全追溯', path: '' },
  { title: '盘点管理', desc: '差异自动调整', path: '' },
  { title: 'V4 数据迁移', desc: 'ETL + 对账', path: '' },
];

export default function ScmPage() {
  const navigate = useNavigate();
  return (
    <div className="p-6">
      <PageHeader title="供应链管理" icon={<Truck className="text-orange-500" size={24} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(item => (
          <div
            key={item.title}
            onClick={() => item.path && navigate(item.path)}
            className={`bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] transition ${item.path ? 'cursor-pointer hover:shadow-md hover:border-orange-300' : 'opacity-60'}`}
          >
            <h3 className="font-medium">{item.title}</h3>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">{item.desc}</p>
            {!item.path && <span className="text-xs text-[hsl(215.4,16.3%,46.9%)] mt-2 inline-block">即将上线</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
