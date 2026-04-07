import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { mgmtApi, type JournalEntry, type GLAccount } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

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
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['journals'], queryFn: mgmtApi.listJournals });
  const { data: accounts } = useQuery({ queryKey: ['gl-accounts'], queryFn: mgmtApi.listAccounts });

  const [open, setOpen] = useState(false);
  const [entryDate, setEntryDate] = useState('');
  const [memo, setMemo] = useState('');
  const [debitAccountId, setDebitAccountId] = useState('');
  const [debitAmount, setDebitAmount] = useState('');
  const [creditAccountId, setCreditAccountId] = useState('');
  const [creditAmount, setCreditAmount] = useState('');

  const handleCreate = async () => {
    await mgmtApi.createJournal({
      date: entryDate,
      description: memo,
      lines: [
        { account_id: debitAccountId, debit_amount: Number(debitAmount) || 0, credit_amount: 0, description: memo },
        { account_id: creditAccountId, debit_amount: 0, credit_amount: Number(creditAmount) || 0, description: memo },
      ],
    });
    qc.invalidateQueries({ queryKey: ['journals'] });
    setEntryDate('');
    setMemo('');
    setDebitAccountId('');
    setDebitAmount('');
    setCreditAccountId('');
    setCreditAmount('');
  };

  const acctList = (accounts || []) as GLAccount[];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader
        title="记账凭证"
        subtitle="Journal Entries"
        icon={<BookOpen size={22} strokeWidth={1.5} />}
        actionLabel="新建"
        onAction={() => setOpen(true)}
      />
      <DataTable<JournalEntry> columns={columns} data={data || []} loading={isLoading} />

      <FormDialog open={open} onClose={() => setOpen(false)} title="新建凭证" onSubmit={handleCreate}>
        <FormField label="日期">
          <FormInput type="date" value={entryDate} onChange={e => setEntryDate(e.target.value)} required />
        </FormField>
        <FormField label="摘要">
          <FormInput value={memo} onChange={e => setMemo(e.target.value)} placeholder="请输入凭证摘要" required />
        </FormField>
        <div style={{ borderTop: '1px solid var(--divider)', paddingTop: '12px', marginTop: '4px' }}>
          <p className="text-[13px] font-medium mb-3" style={{ color: 'var(--fg-secondary)' }}>借方</p>
        </div>
        <FormField label="借方科目">
          <FormSelect value={debitAccountId} onChange={e => setDebitAccountId(e.target.value)} required>
            <option value="">请选择科目</option>
            {acctList.map(a => <option key={a.id} value={a.id}>{a.code} - {a.name}</option>)}
          </FormSelect>
        </FormField>
        <FormField label="借方金额">
          <FormInput type="number" value={debitAmount} onChange={e => setDebitAmount(e.target.value)} placeholder="0.00" min="0" step="0.01" required />
        </FormField>
        <div style={{ borderTop: '1px solid var(--divider)', paddingTop: '12px', marginTop: '4px' }}>
          <p className="text-[13px] font-medium mb-3" style={{ color: 'var(--fg-secondary)' }}>贷方</p>
        </div>
        <FormField label="贷方科目">
          <FormSelect value={creditAccountId} onChange={e => setCreditAccountId(e.target.value)} required>
            <option value="">请选择科目</option>
            {acctList.map(a => <option key={a.id} value={a.id}>{a.code} - {a.name}</option>)}
          </FormSelect>
        </FormField>
        <FormField label="贷方金额">
          <FormInput type="number" value={creditAmount} onChange={e => setCreditAmount(e.target.value)} placeholder="0.00" min="0" step="0.01" required />
        </FormField>
      </FormDialog>
    </div>
  );
}
