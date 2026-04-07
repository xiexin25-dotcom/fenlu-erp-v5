import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCard } from 'lucide-react';
import { mgmtApi, type APRecord, type ARRecord } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const apColumns: Column<APRecord>[] = [
  { key: 'supplier_name', header: '供应商' },
  { key: 'amount', header: '金额', className: 'text-right', render: r => r.amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'paid_amount', header: '已付', className: 'text-right', render: r => r.paid_amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'due_date', header: '到期日', render: r => r.due_date?.slice(0, 10) },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

const arColumns: Column<ARRecord>[] = [
  { key: 'customer_name', header: '客户' },
  { key: 'amount', header: '金额', className: 'text-right', render: r => r.amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'received_amount', header: '已收', className: 'text-right', render: r => r.received_amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'due_date', header: '到期日', render: r => r.due_date?.slice(0, 10) },
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function APARList() {
  const [tab, setTab] = useState<'ap' | 'ar'>('ap');
  const { data: apData, isLoading: apLoading } = useQuery({ queryKey: ['ap'], queryFn: () => mgmtApi.listAP() });
  const { data: arData, isLoading: arLoading } = useQuery({ queryKey: ['ar'], queryFn: () => mgmtApi.listAR() });

  return (
    <div className="p-6">
      <PageHeader title="应付 / 应收" subtitle="AP / AR" icon={<CreditCard className="text-indigo-500" size={24} />} />
      <div className="flex gap-1 mb-4 bg-[hsl(210,40%,96.1%)] p-1 rounded-lg w-fit">
        <button onClick={() => setTab('ap')} className={`px-4 py-1.5 text-sm rounded-md transition ${tab === 'ap' ? 'bg-white shadow font-medium' : 'hover:bg-white/50'}`}>应付账款 (AP)</button>
        <button onClick={() => setTab('ar')} className={`px-4 py-1.5 text-sm rounded-md transition ${tab === 'ar' ? 'bg-white shadow font-medium' : 'hover:bg-white/50'}`}>应收账款 (AR)</button>
      </div>
      {tab === 'ap'
        ? <DataTable<APRecord> columns={apColumns} data={apData || []} loading={apLoading} emptyText="暂无应付记录" />
        : <DataTable<ARRecord> columns={arColumns} data={arData || []} loading={arLoading} emptyText="暂无应收记录" />
      }
    </div>
  );
}
