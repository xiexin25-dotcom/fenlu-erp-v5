import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ShoppingBag, DollarSign, Truck as TruckIcon, AlertCircle, CheckCircle } from 'lucide-react';
import { api, plmApi } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import FormDialog, { FormField, FormInput, FormSelect } from '@/components/FormDialog';

interface SalesOrder {
  id: string; order_no: string; customer_id: string; customer_name: string;
  order_status: string; payment_status: string; shipment_status: string;
  total_amount: string; paid_amount: string; balance: string;
  order_date: string; delivery_date: string | null; shipped_date: string | null;
  salesperson: string | null; items: Array<{ product_name: string; quantity: string; amount: string }>;
}

interface SalesStats {
  total_orders: number; unpaid_unshipped: number; paid_unshipped: number;
  unpaid_shipped: number; total_receivable: number;
}

function money(v: unknown): string {
  const n = typeof v === 'string' ? parseFloat(v) : (typeof v === 'number' ? v : 0);
  return (n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const paymentLabels: Record<string, { label: string; color: string }> = {
  unpaid: { label: '未付款', color: 'var(--status-red-fg)' },
  partial: { label: '部分付款', color: 'var(--status-amber-fg)' },
  paid: { label: '已付清', color: 'var(--status-green-fg)' },
};
const shipmentLabels: Record<string, { label: string; color: string }> = {
  unshipped: { label: '未发货', color: 'var(--status-red-fg)' },
  partial: { label: '部分发货', color: 'var(--status-amber-fg)' },
  shipped: { label: '已发货', color: 'var(--status-blue-fg)' },
  delivered: { label: '已签收', color: 'var(--status-green-fg)' },
};

function StatCard({ label, value, color, icon: Icon }: { label: string; value: number | string; color: string; icon: typeof DollarSign }) {
  return (
    <div className="flex items-center gap-3 p-4" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
      <Icon size={20} style={{ color }} />
      <div>
        <div className="text-[20px] font-semibold" style={{ color }}>{value}</div>
        <div className="text-[12px]" style={{ color: 'var(--fg-tertiary)' }}>{label}</div>
      </div>
    </div>
  );
}

export default function SalesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [showPayment, setShowPayment] = useState<string | null>(null);
  const [payAmount, setPayAmount] = useState('');
  const [filter, setFilter] = useState('');
  const [confirm, setConfirm] = useState<{ id: string; action: string; title: string; msg: string } | null>(null);
  const [form, setForm] = useState({ order_no: '', customer_id: '', customer_name: '', order_date: '', delivery_date: '', salesperson: '', product_id: '', product_name: '', qty: '', price: '' });

  const { data: orders, isLoading } = useQuery({ queryKey: ['sales-orders', filter], queryFn: () => api.get<SalesOrder[]>(`/sales${filter ? `?${filter}` : ''}`) });
  const { data: stats } = useQuery({ queryKey: ['sales-stats'], queryFn: () => api.get<SalesStats>('/sales/stats/summary') });
  const { data: custs } = useQuery({ queryKey: ['customers-all'], queryFn: plmApi.listCustomers });
  const { data: prods } = useQuery({ queryKey: ['products-all'], queryFn: () => plmApi.listProducts(0, 100) });

  const columns: Column<SalesOrder>[] = [
    { key: 'order_no', header: '订单号', className: 'font-mono' },
    { key: 'customer_name', header: '客户' },
    { key: 'total_amount', header: '订单金额', className: 'text-right', render: r => `¥${money(r.total_amount)}` },
    { key: 'payment_status', header: '付款', render: r => {
      const p = paymentLabels[r.payment_status] || { label: r.payment_status, color: 'var(--fg)' };
      return <span className="text-[12px] font-medium" style={{ color: p.color }}>{p.label}</span>;
    }},
    { key: 'paid_amount', header: '已收款', className: 'text-right', render: r => `¥${money(r.paid_amount)}` },
    { key: 'balance', header: '应收余额', className: 'text-right font-medium', render: r => {
      const b = parseFloat(String(r.balance)) || 0;
      return <span style={{ color: b > 0 ? 'var(--status-red-fg)' : 'var(--status-green-fg)' }}>¥{money(r.balance)}</span>;
    }},
    { key: 'shipment_status', header: '发货', render: r => {
      const s = shipmentLabels[r.shipment_status] || { label: r.shipment_status, color: 'var(--fg)' };
      return <span className="text-[12px] font-medium" style={{ color: s.color }}>{s.label}</span>;
    }},
    { key: 'order_date', header: '订单日期', render: r => r.order_date?.slice(0, 10) },
    { key: 'order_status', header: '状态', render: r => <StatusBadge status={r.order_status} /> },
    { key: 'action', header: '操作', render: r => (
      <div className="flex gap-1">
        {r.order_status === 'draft' && (
          <button onClick={e => { e.stopPropagation(); setConfirm({ id: r.id, action: 'confirm', title: '确认订单', msg: `确认订单 ${r.order_no}（客户: ${r.customer_name}，金额: ¥${money(r.total_amount)}）？确认后不可撤销。` }); }}
            className="px-2 py-1 text-[11px] rounded text-white" style={{ background: 'var(--accent)' }}>确认</button>
        )}
        {r.payment_status !== 'paid' && r.order_status !== 'draft' && (
          <button onClick={e => { e.stopPropagation(); setShowPayment(r.id); setPayAmount(''); }}
            className="px-2 py-1 text-[11px] rounded text-white" style={{ background: 'var(--status-green-fg)' }}>收款</button>
        )}
        {r.shipment_status === 'unshipped' && r.order_status !== 'draft' && (
          <button onClick={e => { e.stopPropagation(); setConfirm({ id: r.id, action: 'ship', title: '确认发货', msg: `确认对订单 ${r.order_no} 执行发货操作？发货后将更新发货状态。` }); }}
            className="px-2 py-1 text-[11px] rounded text-white" style={{ background: 'var(--status-amber-fg)' }}>发货</button>
        )}
      </div>
    )},
  ];

  const s = stats || { total_orders: 0, unpaid_unshipped: 0, paid_unshipped: 0, unpaid_shipped: 0, total_receivable: 0 };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader title="销售管理" subtitle="报价 → 订单 → 发货 → 收款" icon={<ShoppingBag size={22} strokeWidth={1.5} />}
        actionLabel="新建订单" onAction={() => setShowCreate(true)} />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="总订单数" value={s.total_orders} color="var(--accent)" icon={ShoppingBag} />
        <StatCard label="未付款未发货" value={s.unpaid_unshipped} color="var(--status-red-fg)" icon={AlertCircle} />
        <StatCard label="已付款未发货" value={s.paid_unshipped} color="var(--status-amber-fg)" icon={TruckIcon} />
        <StatCard label="应收总额" value={`¥${money(s.total_receivable)}`} color="var(--status-red-fg)" icon={DollarSign} />
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {[
          { label: '全部', value: '' },
          { label: '未付款', value: 'payment=unpaid' },
          { label: '已付清', value: 'payment=paid' },
          { label: '未发货', value: 'shipment=unshipped' },
          { label: '已发货', value: 'shipment=shipped' },
        ].map(f => (
          <button key={f.value} onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-[12px] rounded ${filter === f.value ? 'text-white' : ''}`}
            style={{ background: filter === f.value ? 'var(--accent)' : 'var(--bg-hover)', color: filter === f.value ? 'white' : 'var(--fg-secondary)' }}>
            {f.label}
          </button>
        ))}
      </div>

      <DataTable<SalesOrder> columns={columns} data={orders || []} loading={isLoading} />

      {/* Create */}
      <FormDialog open={showCreate} onClose={() => setShowCreate(false)} title="新建销售订单" onSubmit={async () => {
        const cust = (custs || []).find(c => c.id === form.customer_id);
        const prod = (prods?.items || []).find(p => p.id === form.product_id);
        await api.post('/sales', {
          order_no: form.order_no, customer_id: form.customer_id, customer_name: cust?.name || '',
          order_date: form.order_date, delivery_date: form.delivery_date || undefined,
          salesperson: form.salesperson || undefined,
          items: [{ product_id: form.product_id, product_name: prod?.name || '', quantity: Number(form.qty), unit_price: Number(form.price) }],
        });
        qc.invalidateQueries({ queryKey: ['sales-orders'] });
        qc.invalidateQueries({ queryKey: ['sales-stats'] });
      }}>
        <FormField label="订单号"><FormInput value={form.order_no} onChange={e => setForm(f => ({ ...f, order_no: e.target.value }))} placeholder="SO-20260401-001" required /></FormField>
        <FormField label="客户">
          <FormSelect value={form.customer_id} onChange={e => setForm(f => ({ ...f, customer_id: e.target.value }))} required>
            <option value="">选择客户</option>
            {(custs || []).map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
          </FormSelect>
        </FormField>
        <FormField label="订单日期"><FormInput type="date" value={form.order_date} onChange={e => setForm(f => ({ ...f, order_date: e.target.value }))} required /></FormField>
        <FormField label="交货日期"><FormInput type="date" value={form.delivery_date} onChange={e => setForm(f => ({ ...f, delivery_date: e.target.value }))} /></FormField>
        <FormField label="销售员"><FormInput value={form.salesperson} onChange={e => setForm(f => ({ ...f, salesperson: e.target.value }))} /></FormField>
        <div style={{ borderTop: '1px solid var(--divider)', paddingTop: '12px', marginTop: '4px' }}>
          <p className="text-[13px] font-medium mb-3" style={{ color: 'var(--fg-secondary)' }}>产品明细</p>
        </div>
        <FormField label="产品">
          <FormSelect value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))} required>
            <option value="">选择产品</option>
            {(prods?.items || []).map(p => <option key={p.id} value={p.id}>{p.name} ({p.code})</option>)}
          </FormSelect>
        </FormField>
        <FormField label="数量"><FormInput type="number" value={form.qty} onChange={e => setForm(f => ({ ...f, qty: e.target.value }))} min="1" required /></FormField>
        <FormField label="单价"><FormInput type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} min="0" step="0.01" required /></FormField>
      </FormDialog>

      {/* Payment */}
      <FormDialog open={!!showPayment} onClose={() => setShowPayment(null)} title="登记收款" onSubmit={async () => {
        if (showPayment) {
          await api.post(`/sales/${showPayment}/payment`, { amount: Number(payAmount) });
          qc.invalidateQueries({ queryKey: ['sales-orders'] });
          qc.invalidateQueries({ queryKey: ['sales-stats'] });
        }
      }} submitLabel="确认收款">
        <FormField label="收款金额 (¥)">
          <FormInput type="number" value={payAmount} onChange={e => setPayAmount(e.target.value)} min="0.01" step="0.01" placeholder="0.00" required />
        </FormField>
      </FormDialog>

      {/* Confirm Dialog */}
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0" onClick={() => setConfirm(null)}
            style={{ background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(4px)' }} />
          <div className="relative w-full max-w-md mx-4 p-6" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-xl)' }}>
            <h3 className="text-[17px] font-semibold mb-3" style={{ color: 'var(--fg)' }}>{confirm.title}</h3>
            <p className="text-[14px] mb-6" style={{ color: 'var(--fg-secondary)' }}>{confirm.msg}</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirm(null)}
                className="px-4 py-2 text-[13px] rounded-lg" style={{ background: 'var(--bg-hover)', color: 'var(--fg-secondary)' }}>
                取消
              </button>
              <button onClick={async () => {
                if (confirm.action === 'confirm') {
                  await api.post(`/sales/${confirm.id}/confirm`);
                } else if (confirm.action === 'ship') {
                  await api.post(`/sales/${confirm.id}/ship`);
                }
                qc.invalidateQueries({ queryKey: ['sales-orders'] });
                qc.invalidateQueries({ queryKey: ['sales-stats'] });
                setConfirm(null);
              }} className="px-4 py-2 text-[13px] font-medium rounded-lg text-white"
                style={{ background: confirm.action === 'ship' ? 'var(--status-amber-fg)' : 'var(--accent)' }}>
                确认执行
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
