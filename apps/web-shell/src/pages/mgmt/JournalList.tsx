import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { mgmtApi, type JournalEntry } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

function money(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v) || 0;
  return 0;
}

function fmtMoney(n: number): string {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

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
    const lines = rec.lines as Array<{ debit_amount?: unknown }> | undefined;
    const total = lines?.reduce((sum, l) => sum + money(l.debit_amount), 0) ?? 0;
    return fmtMoney(total);
  }},
  { key: 'total_credit', header: '贷方合计', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const lines = rec.lines as Array<{ credit_amount?: unknown }> | undefined;
    const total = lines?.reduce((sum, l) => sum + money(l.credit_amount), 0) ?? 0;
    return fmtMoney(total);
  }},
  { key: 'balance', header: '平衡', className: 'w-16', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const lines = rec.lines as Array<{ debit_amount?: unknown; credit_amount?: unknown }> | undefined;
    const debit = lines?.reduce((sum, l) => sum + money(l.debit_amount), 0) ?? 0;
    const credit = lines?.reduce((sum, l) => sum + money(l.credit_amount), 0) ?? 0;
    const diff = Math.abs(debit - credit);
    return diff < 0.01
      ? <span className="text-xs font-medium" style={{ color: 'var(--status-green-fg)' }}>OK</span>
      : <span className="text-xs font-medium" style={{ color: 'var(--status-red-fg)' }}>差{fmtMoney(diff)}</span>;
  }},
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function JournalList() {
  const { data, isLoading } = useQuery({ queryKey: ['journals'], queryFn: mgmtApi.listJournals });

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="记账凭证" subtitle="Journal Entries" icon={<BookOpen size={22} strokeWidth={1.5} />} />
      <DataTable<JournalEntry> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
