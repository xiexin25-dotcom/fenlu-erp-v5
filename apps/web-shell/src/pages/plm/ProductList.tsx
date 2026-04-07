import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Package } from 'lucide-react';
import { plmApi, type Product } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const categoryLabels: Record<string, string> = {
  self_made: '自制件', raw_material: '原材料', agent: '代理品',
  packaging: '包装材料', semi_finished: '半成品', finished: '成品',
};

const columns: Column<Product>[] = [
  { key: 'code', header: '产品编码', className: 'font-mono' },
  { key: 'name', header: '产品名称' },
  { key: 'category', header: '类别', render: r => categoryLabels[r.category] || r.category },
  { key: 'uom', header: '单位', className: 'w-16', render: r => (r as unknown as Record<string, string>).uom || '' },
  { key: 'current_version', header: '版本', className: 'w-20', render: r => r.current_version?.toString() || '' },
  { key: 'is_active', header: '状态', className: 'w-20', render: r => <StatusBadge status={(r as unknown as Record<string, boolean>).is_active ? 'active' : 'inactive'} /> },
];

export default function ProductList() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', category: 'self_made', uom: 'pcs' });

  const { data: raw, isLoading } = useQuery({
    queryKey: ['products', page],
    queryFn: () => plmApi.listProducts((page - 1) * 20, 20),
  });
  const data = raw?.items || [];
  const total = raw?.total;

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader
        title="产品主数据"
        subtitle="Product Master"
        icon={<Package size={22} strokeWidth={1.5} />}
        actionLabel="新建产品"
        onAction={() => setShowCreate(true)}
      />
      <DataTable<Product>
        columns={columns}
        data={data}
        total={total}
        loading={isLoading}
        page={page}
        onPageChange={setPage}
        onRowClick={r => navigate(`/plm/products/${r.id}`)}
      />
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建产品" onSubmit={async () => {
        await plmApi.createProduct(form);
        qc.invalidateQueries({ queryKey: ['products'] });
        setForm({ code: '', name: '', category: 'self_made', uom: 'pcs' });
      }}>
        <FormField label="产品编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="产品名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="类别">
          <FormSelect value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
            <option value="self_made">自制件</option>
            <option value="raw_material">原材料</option>
            <option value="agent">代理品</option>
            <option value="packaging">包装材料</option>
          </FormSelect>
        </FormField>
        <FormField label="单位"><FormInput value={form.uom} onChange={e => setForm(f => ({ ...f, uom: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
