import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Package } from 'lucide-react';
import { plmApi, type Product } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const columns: Column<Product>[] = [
  { key: 'code', header: '产品编码', className: 'font-mono' },
  { key: 'name', header: '产品名称' },
  { key: 'category', header: '类别' },
  { key: 'unit', header: '单位', className: 'w-16' },
  { key: 'current_version', header: '版本', className: 'w-16', render: r => `V${r.current_version}` },
  { key: 'status', header: '状态', className: 'w-20', render: r => <StatusBadge status={r.status} /> },
  { key: 'created_at', header: '创建时间', render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
];

export default function ProductList() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', category: '', unit: 'pcs' });

  const { data: raw, isLoading } = useQuery({
    queryKey: ['products', page],
    queryFn: () => plmApi.listProducts((page - 1) * 20, 20),
  });
  const data = raw?.items || [];
  const total = raw?.total;

  return (
    <div className="p-6">
      <PageHeader
        title="产品主数据"
        subtitle="Product Master"
        icon={<Package className="text-blue-500" size={24} />}
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
        setForm({ code: '', name: '', category: '', unit: 'pcs' });
      }}>
        <FormField label="产品编码"><FormInput value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required /></FormField>
        <FormField label="产品名称"><FormInput value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required /></FormField>
        <FormField label="类别">
          <FormSelect value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
            <option value="">选择类别</option>
            <option value="raw_material">原材料</option>
            <option value="semi_finished">半成品</option>
            <option value="finished">成品</option>
            <option value="consumable">耗材</option>
          </FormSelect>
        </FormField>
        <FormField label="单位"><FormInput value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))} /></FormField>
      </FormDialog>
    </div>
  );
}
