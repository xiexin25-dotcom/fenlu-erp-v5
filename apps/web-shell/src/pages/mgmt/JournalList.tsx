import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { mgmtApi, type JournalEntry } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<JournalEntry>[] = [
  { key: 'entry_number', header: '凭证号', className: 'font-mono' },
  { key: 'date', header: '日期', render: r => r.date?.slice(0, 10) },
  { key: 'description', header: '摘要' },
  { key: 'total_debit', header: '借方合计', className: 'text-right', render: r => (r.total_debit ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'total_credit', header: '贷方合计', className: 'text-right', render: r => (r.total_credit ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) },
  { key: 'balance', header: '平衡', className: 'w-16', render: r => {
    const diff = Math.abs((r.total_debit ?? 0) - (r.total_credit ?? 0));
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
