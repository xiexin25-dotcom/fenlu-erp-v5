import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { GitBranch } from 'lucide-react';
import { api, plmApi, type ECN } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

const statusLabels: Record<string, string> = {
  draft: '草稿', reviewing: '审核中', approved: '已批准', released: '已发布', effective: '已生效',
};

export default function ECNList() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ product_id: '', ecn_no: '', title: '', reason: '', description: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['ecn-list'],
    queryFn: () => api.get<ECN[]>('/plm/ecn'),
  });

  const { data: prodData } = useQuery({ queryKey: ['products-all'], queryFn: () => plmApi.listProducts(0, 100) });

  const prodMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const p of prodData?.items || []) m[p.id] = `${p.name} (${p.code})`;
    return m;
  }, [prodData]);

  const prodOptions = useMemo(() => prodData?.items || [], [prodData]);

  const columns: Column<ECN>[] = [
    { key: 'ecn_no', header: 'ECN 编号', className: 'font-mono', render: r => (r as unknown as Record<string, string>).ecn_no || '' },
    { key: 'title', header: '变更标题' },
    { key: 'product', header: '关联产品', render: r => {
      const pid = (r as unknown as Record<string, string>).product_id;
      return prodMap[pid] || pid?.slice(0, 8) || '';
    }},
    { key: 'reason', header: '变更原因', render: r => (r as unknown as Record<string, string>).reason || '—' },
    { key: 'status', header: '状态', render: r => {
      const s = r.status;
      return <StatusBadge status={s} />;
    }},
    { key: 'created_at', header: '创建时间', render: r => r.created_at ? new Date(r.created_at).toLocaleDateString('zh-CN') : '' },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="ECN 工程变更" subtitle="Engineering Change Notice" icon={<GitBranch size={22} strokeWidth={1.5} />}
        actionLabel="新建变更" onAction={() => setShowCreate(true)} />
      <DataTable<ECN> columns={columns} data={data || []} loading={isLoading} />

      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建工程变更申请" onSubmit={async () => {
        await api.post('/plm/ecn', {
          product_id: form.product_id,
          ecn_no: form.ecn_no,
          title: form.title,
          reason: form.reason || undefined,
          description: form.description || undefined,
        });
        qc.invalidateQueries({ queryKey: ['ecn-list'] });
        setForm({ product_id: '', ecn_no: '', title: '', reason: '', description: '' });
      }} submitLabel="提交申请">
        <FormField label="关联产品">
          <FormSelect value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))} required>
            <option value="">选择产品</option>
            {prodOptions.map(p => <option key={p.id} value={p.id}>{p.name} ({p.code})</option>)}
          </FormSelect>
        </FormField>
        <FormField label="ECN 编号">
          <FormInput value={form.ecn_no} onChange={e => setForm(f => ({ ...f, ecn_no: e.target.value }))} placeholder="如 ECN-2026-0021" required />
        </FormField>
        <FormField label="变更标题">
          <FormInput value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="简要描述变更内容" required />
        </FormField>
        <FormField label="变更原因">
          <FormSelect value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}>
            <option value="">选择原因</option>
            <option value="客户要求">客户要求</option>
            <option value="降低成本">降低成本</option>
            <option value="质量改进">质量改进</option>
            <option value="安全合规">安全合规</option>
            <option value="工艺优化">工艺优化</option>
            <option value="供应商切换">供应商切换</option>
            <option value="环保法规">环保法规</option>
            <option value="新增功能">新增功能</option>
          </FormSelect>
        </FormField>
        <FormField label="详细描述">
          <FormInput value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="变更详细说明（选填）" />
        </FormField>
      </FormDialog>
    </div>
  );
}
