import { useQuery } from '@tanstack/react-query';
import { dashboardApi, type DashboardData, type KPI } from '@/lib/api';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, Zap, DollarSign, Activity } from 'lucide-react';

function StatCard({ title, value, unit, icon: Icon, trend }: {
  title: string; value: string | number; unit?: string;
  icon: typeof TrendingUp; trend?: 'up' | 'down';
}) {
  return (
    <div
      className="p-5"
      style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[12px] font-medium uppercase tracking-wider" style={{ color: 'var(--fg-tertiary)' }}>{title}</span>
        <Icon size={16} strokeWidth={1.5} style={{ color: 'var(--fg-tertiary)' }} />
      </div>
      <div className="flex items-end gap-1.5">
        <span className="text-[26px] font-semibold tracking-tight" style={{ color: 'var(--fg)' }}>{value}</span>
        {unit && <span className="text-[13px] mb-1" style={{ color: 'var(--fg-tertiary)' }}>{unit}</span>}
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-2">
          {trend === 'up'
            ? <TrendingUp size={12} style={{ color: 'var(--status-green-fg)' }} />
            : <TrendingDown size={12} style={{ color: 'var(--status-red-fg)' }} />}
          <span className="text-[11px]" style={{ color: trend === 'up' ? 'var(--status-green-fg)' : 'var(--status-red-fg)' }}>
            {trend === 'up' ? '+5.2%' : '-2.1%'} vs last week
          </span>
        </div>
      )}
    </div>
  );
}

function KPIGauge({ kpi }: { kpi: KPI }) {
  const pct = Math.min(100, Math.round((kpi.current_value / kpi.target_value) * 100));
  const color = pct >= 90 ? 'var(--status-green-fg)' : pct >= 70 ? 'var(--status-amber-fg)' : 'var(--status-red-fg)';
  return (
    <div className="py-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[13px]" style={{ color: 'var(--fg)' }}>{kpi.name}</span>
        <span className="text-[12px] font-medium" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-[5px] rounded-full overflow-hidden" style={{ background: 'var(--divider)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
}

const mockDashboard: DashboardData = {
  today_revenue: 285600, weekly_output: 12450, weekly_oee: 87.3,
  open_safety_hazards: 2, energy_unit_consumption: 3.42, cash_position: 4520000,
  revenue_trend: [
    { date: '03-31', amount: 240000 }, { date: '04-01', amount: 268000 },
    { date: '04-02', amount: 255000 }, { date: '04-03', amount: 292000 },
    { date: '04-04', amount: 278000 }, { date: '04-05', amount: 301000 },
    { date: '04-06', amount: 285600 },
  ],
  oee_trend: [
    { date: '03-31', oee: 85.1 }, { date: '04-01', oee: 86.4 },
    { date: '04-02', oee: 84.8 }, { date: '04-03', oee: 87.9 },
    { date: '04-04', oee: 88.2 }, { date: '04-05', oee: 86.7 },
    { date: '04-06', oee: 87.3 },
  ],
};

const mockKPIs: KPI[] = [
  { code: 'OEE', name: 'OEE 综合效率', unit: '%', current_value: 87.3, target_value: 90 },
  { code: 'QC_PASS', name: '质检合格率', unit: '%', current_value: 98.2, target_value: 99 },
  { code: 'DELIVERY', name: '准时交付率', unit: '%', current_value: 94.5, target_value: 95 },
  { code: 'SAFETY', name: '安全事故率', unit: 'ppm', current_value: 0.5, target_value: 1 },
  { code: 'ENERGY', name: '能耗达标率', unit: '%', current_value: 92.1, target_value: 95 },
  { code: 'INVENTORY', name: '库存周转率', unit: '次/月', current_value: 4.2, target_value: 5 },
];

const scenarioData = [
  { name: '产品设计', score: 3 }, { name: '工艺设计', score: 3 },
  { name: '计划排程', score: 3 }, { name: '生产管控', score: 3 },
  { name: '质量管理', score: 3 }, { name: '设备管理', score: 3 },
  { name: '安全生产', score: 3 }, { name: '能耗管理', score: 3 },
  { name: '采购管理', score: 3 }, { name: '仓储物流', score: 3 },
  { name: '财务管理', score: 3 }, { name: '人力资源', score: 2 },
  { name: '营销管理', score: 3 }, { name: '售后服务', score: 3 },
  { name: '协同办公', score: 2 }, { name: '决策支持', score: 3 },
];

export default function Dashboard() {
  const { data: dashboard } = useQuery({ queryKey: ['dashboard'], queryFn: dashboardApi.exec, retry: false });
  const d = dashboard && dashboard.today_revenue !== undefined ? dashboard : mockDashboard;
  // Dashboard KPIs use curated mock data (detailed KPI data is on /mgmt/kpi page)
  const k = mockKPIs;

  const cardStyle: React.CSSProperties = { background: 'var(--bg-card)', borderRadius: 'var(--radius)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-[28px] font-semibold tracking-tight" style={{ color: 'var(--fg)' }}>领导驾驶舱</h1>
          <p className="text-[14px] mt-0.5" style={{ color: 'var(--fg-tertiary)' }}>决策支持 - 三级集成级</p>
        </div>
        <span className="text-[13px]" style={{ color: 'var(--fg-tertiary)' }}>{new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}</span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        <StatCard title="今日营收" value={((d.today_revenue ?? 0) / 10000).toFixed(1)} unit="万元" icon={DollarSign} trend="up" />
        <StatCard title="本周产量" value={(d.weekly_output ?? 0).toLocaleString()} unit="件" icon={Activity} trend="up" />
        <StatCard title="OEE" value={(d.weekly_oee ?? 0).toFixed(1)} unit="%" icon={TrendingUp} trend="up" />
        <StatCard title="安全隐患" value={d.open_safety_hazards ?? 0} unit="项" icon={AlertTriangle} />
        <StatCard title="单耗" value={(d.energy_unit_consumption ?? 0).toFixed(2)} unit="kWh/件" icon={Zap} trend="down" />
        <StatCard title="现金头寸" value={((d.cash_position ?? 0) / 10000).toFixed(0)} unit="万元" icon={DollarSign} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="p-6" style={cardStyle}>
          <h3 className="text-[14px] font-semibold mb-5" style={{ color: 'var(--fg)' }}>营收趋势</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.revenue_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--fg-tertiary)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--fg-tertiary)' }} tickFormatter={v => `${(v/10000).toFixed(0)}万`} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => [`${(Number(v)/10000).toFixed(1)}万元`, '营收']} contentStyle={{ borderRadius: 8, border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)', fontSize: 12 }} />
              <Bar dataKey="amount" fill="var(--accent)" radius={[6, 6, 0, 0]} barSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="p-6" style={cardStyle}>
          <h3 className="text-[14px] font-semibold mb-5" style={{ color: 'var(--fg)' }}>OEE 趋势</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={d.oee_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--fg-tertiary)' }} axisLine={false} tickLine={false} />
              <YAxis domain={[80, 95]} tick={{ fontSize: 11, fill: 'var(--fg-tertiary)' }} tickFormatter={v => `${v}%`} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => [`${v}%`, 'OEE']} contentStyle={{ borderRadius: 8, border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)', fontSize: 12 }} />
              <Line type="monotone" dataKey="oee" stroke="var(--status-purple-fg)" strokeWidth={2.5} dot={{ r: 3, fill: 'var(--bg-card)', stroke: 'var(--status-purple-fg)', strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="p-6" style={cardStyle}>
          <h3 className="text-[14px] font-semibold mb-4" style={{ color: 'var(--fg)' }}>KPI 达成率</h3>
          {k.map(kpi => <KPIGauge key={kpi.code} kpi={kpi} />)}
        </div>

        <div className="p-6 lg:col-span-2" style={cardStyle}>
          <h3 className="text-[14px] font-semibold mb-5" style={{ color: 'var(--fg)' }}>工信部 16 场景评测</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={scenarioData} layout="vertical" margin={{ left: 70 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" horizontal={false} />
              <XAxis type="number" domain={[0, 3]} ticks={[0, 1, 2, 3]} tick={{ fontSize: 11, fill: 'var(--fg-tertiary)' }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: 'var(--fg-secondary)' }} width={65} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => [`${v}级`, '等级']} contentStyle={{ borderRadius: 8, border: '1px solid var(--border)', fontSize: 12 }} />
              <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={14}>
                {scenarioData.map((entry, i) => (
                  <Cell key={i} fill={entry.score >= 3 ? 'var(--status-green-fg)' : 'var(--status-amber-fg)'} opacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
