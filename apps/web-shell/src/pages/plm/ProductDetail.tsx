import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Package } from 'lucide-react';
import { plmApi } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: () => plmApi.getProduct(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-6 text-center text-[hsl(215.4,16.3%,46.9%)]">Loading...</div>;
  if (!product) return <div className="p-6 text-center">产品不存在</div>;

  return (
    <div className="p-6">
      <button onClick={() => navigate('/plm/products')} className="flex items-center gap-1 text-sm text-[hsl(215.4,16.3%,46.9%)] hover:text-[hsl(222.2,84%,4.9%)] mb-4 transition">
        <ArrowLeft size={16} /> 返回列表
      </button>
      <div className="bg-white rounded-xl p-6 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
        <div className="flex items-center gap-3 mb-6">
          <Package className="text-blue-500" size={28} />
          <div>
            <h1 className="text-xl font-bold">{product.name}</h1>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] font-mono">{product.code}</p>
          </div>
          <StatusBadge status={product.status} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '类别', value: product.category },
            { label: '单位', value: product.unit },
            { label: '当前版本', value: `V${product.current_version}` },
            { label: '创建时间', value: new Date(product.created_at).toLocaleDateString('zh-CN') },
          ].map(item => (
            <div key={item.label} className="bg-[hsl(210,40%,98%)] rounded-lg p-3">
              <p className="text-xs text-[hsl(215.4,16.3%,46.9%)] mb-1">{item.label}</p>
              <p className="font-medium">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
