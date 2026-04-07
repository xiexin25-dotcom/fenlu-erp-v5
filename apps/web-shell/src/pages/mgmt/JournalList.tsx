import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { mgmtApi, type JournalEntry } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<JournalEntry>[] = [
  { key: 'entry_no', header: '凭证号', className: 'font-mono', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.entry_no as string) || '—';
  }},
  { key: 'entry_date', header: '日期', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.entry_date as string | undefined;
    return val ? val.slice(0, 10) : '—';
  }},
  { key: 'memo', header: '摘要', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.memo as string) || '—';
  }},
  { key: 'total_debit', header: '借方合计', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const lines = rec.lines as Array<{ debit_amount?: number }> | undefined;
    const total = lines?.reduce((sum, l) => sum + (l.debit_amount ?? 0), 0) ?? 0;
    return total.toLocaleString('zh-CN', { minimumFractionDigits: 2 });
  }},
  { key: 'total_credit', header: '贷方合计', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const lines = rec.lines as Array<{ credit_amount?: number }> | undefined;
    const total = lines?.reduce((sum, l) => sum + (l.credit_amount ?? 0), 0) ?? 0;
    return total.toLocaleString('zh-CN', { minimumFractionDigits: 2 });
  }},
  { key: 'balance', header: '平衡', className: 'w-16', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const lines = rec.lines as Array<{ debit_amount?: number; credit_amount?: number }> | undefined;
    const debit = lines?.reduce((sum, l) => sum + (l.debit_amount ?? 0), 0) ?? 0;
    const credit = lines?.reduce((sum, l) => sum + (l.credit_amount ?? 0), 0) ?? 0;
    const diff = Math.abs(debit - credit);
    return diff < 0.01
      ? <span className="text-green-600 text-xs font-medium">OK</span>
      : <span className="text-red-600 text-xs font-medium">差{diff.toFixed(2)}</span>;
  }},
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function JournalList() {
  const { data, isLoading } = useQuery({ queryKey: ['journals'], queryFn: mgmtApi.listJournals });

  return (
    <div className="p-6">
      <PageHeader
        title="记账凭证"
        subtitle="Journal Entries"
        icon={<BookOpen className="text-indigo-500" size={24} />}
      />
      <DataTable<JournalEntry>
        columns={columns}
        data={data || []}
        loading={isLoading}
      />
    </div>
  );
}
