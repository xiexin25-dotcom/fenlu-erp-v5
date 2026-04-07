import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Banknote, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

interface PayrollItem {
  id: string; employee_id: string; employee_no: string; employee_name: string;
  base_salary: string; overtime_pay: string; deductions: string; net_pay: string;
}
interface Payroll {
  id: string; period: string; status: string; total_amount: string;
  head_count: number; items: PayrollItem[];
}

function fmt(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const itemColumns: Column<PayrollItem>[] = [
  { key: 'employee_no', header: '工号', className: 'font-mono' },
  { key: 'employee_name', header: '姓名' },
  { key: 'base_salary', header: '基本工资', className: 'text-right', render: r => fmt(r.base_salary) },
  { key: 'overtime_pay', header: '加班费', className: 'text-right', render: r => fmt(r.overtime_pay) },
  { key: 'deductions', header: '扣款', className: 'text-right', render: r => fmt(r.deductions) },
  { key: 'net_pay', header: '实发工资', className: 'text-right font-medium', render: r => fmt(r.net_pay) },
];

function PayrollCard({ payroll }: { payroll: Payroll }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', marginBottom: 12 }}>
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        <div className="flex items-center gap-4">
          {expanded ? <ChevronDown size={16} style={{ color: 'var(--fg-tertiary)' }} /> : <ChevronRight size={16} style={{ color: 'var(--fg-tertiary)' }} />}
          <span className="text-[15px] font-medium">{payroll.period}</span>
          <StatusBadge status={payroll.status} />
        </div>
        <div className="flex items-center gap-6 text-[13px]" style={{ color: 'var(--fg-secondary)' }}>
          <span>{payroll.head_count} 人</span>
          <span className="font-medium" style={{ color: 'var(--fg)' }}>¥{fmt(payroll.total_amount)}</span>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4">
          <DataTable<PayrollItem> columns={itemColumns} data={payroll.items || []} />
        </div>
      )}
    </div>
  );
}

export default function PayrollList() {
  const { data, isLoading } = useQuery({ queryKey: ['payroll'], queryFn: () => api.get<Payroll[]>('/mgmt/hr/payroll') });

  if (isLoading) return <div className="p-8 text-center" style={{ color: 'var(--fg-tertiary)' }}>Loading...</div>;

  const payrolls = data || [];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="薪资管理" subtitle="月度工资条 · 点击展开查看员工明细" icon={<Banknote size={22} strokeWidth={1.5} />} />
      {payrolls.length === 0 ? (
        <div className="text-center py-16" style={{ color: 'var(--fg-tertiary)' }}>暂无工资条</div>
      ) : (
        payrolls.map(p => <PayrollCard key={p.id} payroll={p} />)
      )}
    </div>
  );
}
