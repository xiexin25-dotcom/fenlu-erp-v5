import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Banknote, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

interface PayrollItem {
  id: string; employee_no: string; employee_name: string;
  base_salary: string; overtime_pay: string; deductions: string; gross_pay: string;
  pension_employee: string; medical_employee: string; unemployment_employee: string;
  housing_fund_employee: string; social_insurance_employee: string;
  pension_employer: string; medical_employer: string; unemployment_employer: string;
  injury_employer: string; housing_fund_employer: string; social_insurance_employer: string;
  taxable_income: string; income_tax: string; net_pay: string;
}
interface Payroll {
  id: string; period: string; status: string; total_amount: string;
  head_count: number; items: PayrollItem[];
}

function m(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function PayrollCard({ payroll }: { payroll: Payroll }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', marginBottom: 12 }}>
      <div className="flex items-center justify-between px-5 py-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
        <div className="flex items-center gap-4">
          {expanded ? <ChevronDown size={16} style={{ color: 'var(--fg-tertiary)' }} /> : <ChevronRight size={16} style={{ color: 'var(--fg-tertiary)' }} />}
          <span className="text-[15px] font-medium">{payroll.period}</span>
          <StatusBadge status={payroll.status} />
        </div>
        <div className="flex items-center gap-6 text-[13px]" style={{ color: 'var(--fg-secondary)' }}>
          <span>{payroll.head_count} 人</span>
          <span className="font-medium" style={{ color: 'var(--fg)' }}>实发合计 ¥{m(payroll.total_amount)}</span>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 overflow-x-auto">
          <table className="w-full text-[12px]" style={{ minWidth: 1100 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--divider)' }}>
                <th className="px-2 py-2 text-left font-medium" style={{ color: 'var(--fg-tertiary)' }}>工号</th>
                <th className="px-2 py-2 text-left font-medium" style={{ color: 'var(--fg-tertiary)' }}>姓名</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--fg-tertiary)' }}>基本工资</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--fg-tertiary)' }}>加班费</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--fg-tertiary)' }}>缺勤扣款</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--fg-tertiary)' }}>应发合计</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: '#0071e3' }}>养老8%</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: '#0071e3' }}>医疗2%</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: '#0071e3' }}>失业0.3%</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: '#0071e3' }}>公积金8%</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--status-amber-fg)' }}>应税所得</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--status-red-fg)' }}>个人所得税</th>
                <th className="px-2 py-2 text-right font-medium" style={{ color: 'var(--status-green-fg)' }}>实发工资</th>
              </tr>
            </thead>
            <tbody>
              {payroll.items.map(it => (
                <tr key={it.id} style={{ borderBottom: '1px solid var(--divider)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td className="px-2 py-2 font-mono">{it.employee_no}</td>
                  <td className="px-2 py-2">{it.employee_name}</td>
                  <td className="px-2 py-2 text-right">{m(it.base_salary)}</td>
                  <td className="px-2 py-2 text-right">{m(it.overtime_pay)}</td>
                  <td className="px-2 py-2 text-right">{m(it.deductions)}</td>
                  <td className="px-2 py-2 text-right font-medium">{m(it.gross_pay)}</td>
                  <td className="px-2 py-2 text-right" style={{ color: '#0071e3' }}>{m(it.pension_employee)}</td>
                  <td className="px-2 py-2 text-right" style={{ color: '#0071e3' }}>{m(it.medical_employee)}</td>
                  <td className="px-2 py-2 text-right" style={{ color: '#0071e3' }}>{m(it.unemployment_employee)}</td>
                  <td className="px-2 py-2 text-right" style={{ color: '#0071e3' }}>{m(it.housing_fund_employee)}</td>
                  <td className="px-2 py-2 text-right" style={{ color: 'var(--status-amber-fg)' }}>{m(it.taxable_income)}</td>
                  <td className="px-2 py-2 text-right font-medium" style={{ color: 'var(--status-red-fg)' }}>{m(it.income_tax)}</td>
                  <td className="px-2 py-2 text-right font-medium" style={{ color: 'var(--status-green-fg)' }}>{m(it.net_pay)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function PayrollList() {
  const { data, isLoading } = useQuery({ queryKey: ['payroll'], queryFn: () => api.get<Payroll[]>('/mgmt/hr/payroll') });
  if (isLoading) return <div className="p-8 text-center" style={{ color: 'var(--fg-tertiary)' }}>Loading...</div>;
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader title="薪资管理" subtitle="吉林省标准 · 五险一金 + 个人所得税" icon={<Banknote size={22} strokeWidth={1.5} />} />
      {(data || []).length === 0
        ? <div className="text-center py-16" style={{ color: 'var(--fg-tertiary)' }}>暂无工资条</div>
        : (data || []).map(p => <PayrollCard key={p.id} payroll={p} />)}
    </div>
  );
}
