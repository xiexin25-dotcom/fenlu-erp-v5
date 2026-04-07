import { Truck } from 'lucide-react';

export default function ScmPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Truck className="text-orange-500" size={24} />
        <h1 className="text-xl font-bold">供应链管理</h1>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { title: '供应商管理', desc: '评级 + Tier 转换' },
          { title: '采购管理', desc: 'PR→RFQ→PO→Receipt' },
          { title: '仓库管理', desc: '多仓 + 4级库位' },
          { title: '库存管理', desc: 'StockMove 全追溯' },
          { title: '盘点管理', desc: '差异自动调整' },
          { title: 'V4 数据迁移', desc: 'ETL + 对账' },
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
