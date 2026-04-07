import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCard } from 'lucide-react';
import { mgmtApi, scmApi, plmApi, type APRecord, type ARRecord } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

function money(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v) || 0;
  return 0;
}
function fmt(v: unknown): string {
  return money(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function APARList() {
  const [tab, setTab] = useState<'ap' | 'ar'>('ap');
  const { data: apData, isLoading: apLoading } = useQuery({ queryKey: ['ap'], queryFn: () => mgmtApi.listAP() });
  const { data: arData, isLoading: arLoading } = useQuery({ queryKey: ['ar'], queryFn: () => mgmtApi.listAR() });
  const { data: suppliers } = useQuery({ queryKey: ['suppliers-all'], queryFn: () => scmApi.listSuppliers() });
  const { data: customers } = useQuery({ queryKey: ['customers-all'], queryFn: () => plmApi.listCustomers() });

  const supplierMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const s of suppliers || []) m[s.id] = `${s.name} (${s.code})`;
    return m;
  }, [suppliers]);

  const customerMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const c of customers || []) m[c.id] = `${c.name} (${c.code})`;
    return m;
  }, [customers]);

  const apColumns: Column<APRecord>[] = [
    { key: 'supplier_id', header: '供应商', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      const sid = rec.supplier_id as string;
      return supplierMap[sid] || (sid || '').slice(0, 8);
    }},
    { key: 'total_amount', header: '金额', className: 'text-right', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return fmt(rec.total_amount);
    }},
    { key: 'paid_amount', header: '已付', className: 'text-right', render: r => fmt(r.paid_amount) },
    { key: 'balance', header: '余额', className: 'text-right', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return fmt(rec.balance);
    }},
    { key: 'due_date', header: '到期日', render: r => r.due_date?.slice(0, 10) },
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  ];

  const arColumns: Column<ARRecord>[] = [
    { key: 'customer_id', header: '客户', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      const cid = rec.customer_id as string;
      return customerMap[cid] || (cid || '').slice(0, 8);
    }},
    { key: 'total_amount', header: '金额', className: 'text-right', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return fmt(rec.total_amount);
    }},
    { key: 'received_amount', header: '已收', className: 'text-right', render: r => fmt(r.received_amount) },
    { key: 'balance', header: '余额', className: 'text-right', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return fmt(rec.balance);
    }},
    { key: 'due_date', header: '到期日', render: r => r.due_date?.slice(0, 10) },
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="应付 / 应收" subtitle="AP / AR" icon={<CreditCard size={22} strokeWidth={1.5} />} />
      <div className="flex gap-1 mb-4 p-1 rounded-lg w-fit" style={{ background: 'var(--bg-hover)' }}>
        <button onClick={() => setTab('ap')} className={`px-4 py-1.5 text-sm rounded-md transition ${tab === 'ap' ? 'bg-white shadow font-medium' : ''}`}>应付账款 (AP)</button>
        <button onClick={() => setTab('ar')} className={`px-4 py-1.5 text-sm rounded-md transition ${tab === 'ar' ? 'bg-white shadow font-medium' : ''}`}>应收账款 (AR)</button>
      </div>
      {tab === 'ap'
        ? <DataTable<APRecord> columns={apColumns} data={apData || []} loading={apLoading} emptyText="暂无应付记录" />
        : <DataTable<ARRecord> columns={arColumns} data={arData || []} loading={arLoading} emptyText="暂无应收记录" />
      }
    </div>
  );
}
