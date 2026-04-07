import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileSpreadsheet } from 'lucide-react';
import { api } from '@/lib/api';
import PageHeader from '@/components/PageHeader';

function money(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface StatementItem { code: string; name: string; amount?: number; balance?: number; }
interface BalanceSheet {
  title: string; period: string; as_of: string;
  assets: { items: StatementItem[]; total: number };
  liabilities: { items: StatementItem[]; total: number };
  equity: { items: StatementItem[]; retained_earnings: number; total: number };
  liabilities_and_equity: number; balanced: boolean;
}
interface IncomeStatement {
  title: string; period: string;
  revenue: { items: StatementItem[]; total: number };
  expenses: { items: StatementItem[]; total: number };
  net_income: number;
}
interface CashFlow {
  title: string; period: string;
  operating: { ar_received: number; ap_paid: number; net: number };
  gl_cash_movement: { cash_in: number; cash_out: number; net_change: number };
  net_cash_change: number;
}

function Section({ title, items, total, color }: { title: string; items: StatementItem[]; total: number; color: string }) {
  // Filter out zero-balance and test items
  const filtered = items.filter(it => {
    const v = Math.abs(it.balance ?? it.amount ?? 0);
    return v > 0.01 && !it.code.startsWith('T');
  });
  return (
    <div className="mb-6">
      <h4 className="text-[14px] font-semibold mb-2" style={{ color }}>{title}</h4>
      <table className="w-full text-[13px]">
        <tbody>
          {filtered.map((it, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--divider)' }}>
              <td className="py-2 pl-4 font-mono text-[12px]" style={{ color: 'var(--fg-tertiary)' }}>{it.code}</td>
              <td className="py-2">{it.name}</td>
              <td className="py-2 text-right pr-4">¥{money(it.balance ?? it.amount ?? 0)}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={3} className="py-3 text-center text-[12px]" style={{ color: 'var(--fg-tertiary)' }}>暂无数据</td></tr>
          )}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid var(--border-strong)' }}>
            <td colSpan={2} className="py-2 pl-4 font-medium">合计</td>
            <td className="py-2 text-right pr-4 font-semibold" style={{ color }}>¥{money(total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export default function FinancialStatements() {
  const [tab, setTab] = useState<'balance' | 'income' | 'cashflow'>('balance');
  const [period, setPeriod] = useState('2026-04');

  const { data: bs } = useQuery({
    queryKey: ['stmt-balance', period],
    queryFn: () => api.get<BalanceSheet>(`/mgmt/finance/statements/balance_sheet?period=${period}`),
    enabled: tab === 'balance',
  });
  const { data: inc } = useQuery({
    queryKey: ['stmt-income', period],
    queryFn: () => api.get<IncomeStatement>(`/mgmt/finance/statements/income?period=${period}`),
    enabled: tab === 'income',
  });
  const { data: cf } = useQuery({
    queryKey: ['stmt-cashflow', period],
    queryFn: () => api.get<CashFlow>(`/mgmt/finance/statements/cash_flow?period=${period}`),
    enabled: tab === 'cashflow',
  });

  return (
    <div className="p-8 max-w-[900px] mx-auto">
      <PageHeader title="财务三表" subtitle="资产负债表 · 利润表 · 现金流量表" icon={<FileSpreadsheet size={22} strokeWidth={1.5} />}>
        <input type="month" value={period} onChange={e => setPeriod(e.target.value)}
          className="px-3 py-1.5 text-[13px] rounded-lg outline-none"
          style={{ border: '1px solid var(--border-strong)' }} />
      </PageHeader>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 rounded w-fit" style={{ background: 'var(--bg-hover)' }}>
        {[
          { key: 'balance' as const, label: '资产负债表' },
          { key: 'income' as const, label: '利润表' },
          { key: 'cashflow' as const, label: '现金流量表' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 text-[13px] rounded transition ${tab === t.key ? 'bg-white shadow font-medium' : ''}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }} className="p-6">

        {/* 资产负债表 */}
        {tab === 'balance' && bs && (
          <>
            <div className="text-center mb-6">
              <h3 className="text-[18px] font-semibold">{bs.title}</h3>
              <p className="text-[13px]" style={{ color: 'var(--fg-tertiary)' }}>截至 {bs.as_of}</p>
            </div>
            <Section title="资产" items={bs.assets.items} total={bs.assets.total} color="var(--accent)" />
            <Section title="负债" items={bs.liabilities.items} total={bs.liabilities.total} color="var(--status-red-fg)" />
            <Section title="所有者权益" items={bs.equity.items} total={bs.equity.total} color="var(--status-green-fg)" />
            <div className="flex items-center justify-between pt-4 mt-4" style={{ borderTop: '3px double var(--border-strong)' }}>
              <span className="font-medium">资产 = 负债 + 权益</span>
              <span className={`text-[14px] font-semibold ${bs.balanced ? '' : ''}`} style={{ color: bs.balanced ? 'var(--status-green-fg)' : 'var(--status-red-fg)' }}>
                {bs.balanced ? '✓ 平衡' : '✗ 不平衡'}
              </span>
            </div>
          </>
        )}

        {/* 利润表 */}
        {tab === 'income' && inc && (
          <>
            <div className="text-center mb-6">
              <h3 className="text-[18px] font-semibold">{inc.title}</h3>
              <p className="text-[13px]" style={{ color: 'var(--fg-tertiary)' }}>{period}</p>
            </div>
            <Section title="营业收入" items={inc.revenue.items} total={inc.revenue.total} color="var(--status-green-fg)" />
            <Section title="营业费用" items={inc.expenses.items} total={inc.expenses.total} color="var(--status-red-fg)" />
            <div className="flex items-center justify-between pt-4 mt-4" style={{ borderTop: '3px double var(--border-strong)' }}>
              <span className="text-[16px] font-semibold">净利润</span>
              <span className="text-[18px] font-bold" style={{ color: inc.net_income >= 0 ? 'var(--status-green-fg)' : 'var(--status-red-fg)' }}>
                ¥{money(inc.net_income)}
              </span>
            </div>
          </>
        )}

        {/* 现金流量表 */}
        {tab === 'cashflow' && cf && (
          <>
            <div className="text-center mb-6">
              <h3 className="text-[18px] font-semibold">{cf.title}</h3>
              <p className="text-[13px]" style={{ color: 'var(--fg-tertiary)' }}>{period}</p>
            </div>
            <div className="space-y-4">
              <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                <h4 className="text-[14px] font-semibold mb-3" style={{ color: 'var(--accent)' }}>经营活动现金流</h4>
                <div className="flex justify-between text-[13px] py-1"><span>应收账款收回</span><span>¥{money(cf.operating.ar_received)}</span></div>
                <div className="flex justify-between text-[13px] py-1"><span>应付账款支付</span><span style={{ color: 'var(--status-red-fg)' }}>-¥{money(cf.operating.ap_paid)}</span></div>
                <div className="flex justify-between text-[14px] font-medium pt-2 mt-2" style={{ borderTop: '1px solid var(--divider)' }}>
                  <span>经营活动净额</span><span style={{ color: cf.operating.net >= 0 ? 'var(--status-green-fg)' : 'var(--status-red-fg)' }}>¥{money(cf.operating.net)}</span>
                </div>
              </div>
              <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                <h4 className="text-[14px] font-semibold mb-3" style={{ color: 'var(--status-purple-fg)' }}>现金账户变动</h4>
                <div className="flex justify-between text-[13px] py-1"><span>现金流入</span><span style={{ color: 'var(--status-green-fg)' }}>¥{money(cf.gl_cash_movement.cash_in)}</span></div>
                <div className="flex justify-between text-[13px] py-1"><span>现金流出</span><span style={{ color: 'var(--status-red-fg)' }}>-¥{money(cf.gl_cash_movement.cash_out)}</span></div>
                <div className="flex justify-between text-[14px] font-medium pt-2 mt-2" style={{ borderTop: '1px solid var(--divider)' }}>
                  <span>现金净变动</span><span>¥{money(cf.gl_cash_movement.net_change)}</span>
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 mt-2" style={{ borderTop: '3px double var(--border-strong)' }}>
                <span className="text-[16px] font-semibold">本期现金净增减</span>
                <span className="text-[18px] font-bold" style={{ color: cf.net_cash_change >= 0 ? 'var(--status-green-fg)' : 'var(--status-red-fg)' }}>
                  ¥{money(cf.net_cash_change)}
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
