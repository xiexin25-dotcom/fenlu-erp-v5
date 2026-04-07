import { useQuery } from '@tanstack/react-query';
import { dashboardApi, kpiApi, type DashboardData, type KPI } from '@/lib/api';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, Zap, DollarSign, Activity } from 'lucide-react';

function StatCard({ title, value, unit, icon: Icon, trend, color }: {
  title: string; value: string | number; unit?: string;
  icon: typeof TrendingUp; trend?: 'up' | 'down'; color: string;
}) {
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-[hsl(215.4,16.3%,46.9%)]">{title}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
      <div className="flex items-end gap-1">
        <span className="text-2xl font-bold">{value}</span>
        {unit && <span className="text-sm text-[hsl(215.4,16.3%,46.9%)] mb-0.5">{unit}</span>}
      </div>
      {trend && (
        <div className={`flex items-center gap-1 mt-1 text-xs ${trend === 'up' ? 'text-green-600' : 'text-red-500'}`}>
          {trend === 'up' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          <span>{trend === 'up' ? '+5.2%' : '-2.1%'} vs last week</span>
        </div>
      )}
    </div>
  );
}

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

function KPIGauge({ kpi }: { kpi: KPI }) {
  const pct = Math.min(100, Math.round((kpi.current_value / kpi.target_value) * 100));
  const color = pct >= 90 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm truncate">{kpi.name}</span>
          <span className="text-xs text-[hsl(215.4,16.3%,46.9%)]">{pct}%</span>
        </div>
        <div className="h-2 bg-[hsl(210,40%,96.1%)] rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
    </div>
  );
}

// Mock data for when API is unavailable
const mockDashboard: DashboardData = {
  today_revenue: 285600,
  weekly_output: 12450,
  weekly_oee: 87.3,
  open_safety_hazards: 2,
  energy_unit_consumption: 3.42,
  cash_position: 4520000,
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
  const { data: dashboard } = useQuery({
    queryKey: ['dashboard'], queryFn: dashboardApi.exec,
    retry: false,
  });
  const { data: kpis } = useQuery({
    queryKey: ['kpis'], queryFn: kpiApi.list,
    retry: false,
  });

  const d = dashboard && dashboard.today_revenue !== undefined ? dashboard : mockDashboard;
  const k = kpis && kpis.length > 0 ? kpis : mockKPIs;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">领导驾驶舱</h1>
          <p className="text-sm text-[hsl(215.4,16.3%,46.9%)]">决策支持 - 三级集成级</p>
        </div>
        <span className="text-sm text-[hsl(215.4,16.3%,46.9%)]">{new Date().toLocaleDateString('zh-CN')}</span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard title="今日营收" value={((d.today_revenue ?? 0) / 10000).toFixed(1)} unit="万元" icon={DollarSign} trend="up" color="bg-blue-500" />
        <StatCard title="本周产量" value={(d.weekly_output ?? 0).toLocaleString()} unit="件" icon={Activity} trend="up" color="bg-green-500" />
        <StatCard title="OEE" value={(d.weekly_oee ?? 0).toFixed(1)} unit="%" icon={TrendingUp} trend="up" color="bg-purple-500" />
        <StatCard title="安全隐患" value={d.open_safety_hazards ?? 0} unit="项" icon={AlertTriangle} color="bg-red-500" />
        <StatCard title="单耗" value={(d.energy_unit_consumption ?? 0).toFixed(2)} unit="kWh/件" icon={Zap} trend="down" color="bg-amber-500" />
        <StatCard title="现金头寸" value={((d.cash_position ?? 0) / 10000).toFixed(0)} unit="万元" icon={DollarSign} color="bg-cyan-500" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Trend */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
          <h3 className="text-sm font-medium mb-4">营收趋势 (近7日)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={d.revenue_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `${(v/10000).toFixed(0)}万`} />
              <Tooltip formatter={(v) => [`${(Number(v)/10000).toFixed(1)}万元`, '营收']} />
              <Bar dataKey="amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* OEE Trend */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
          <h3 className="text-sm font-medium mb-4">OEE 趋势 (近7日)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={d.oee_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis domain={[80, 95]} tick={{ fontSize: 12 }} tickFormatter={v => `${v}%`} />
              <Tooltip formatter={(v) => [`${v}%`, 'OEE']} />
              <Line type="monotone" dataKey="oee" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* KPI Progress */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
          <h3 className="text-sm font-medium mb-3">KPI 达成率</h3>
          <div className="space-y-1">
            {k.map(kpi => <KPIGauge key={kpi.code} kpi={kpi} />)}
          </div>
        </div>

        {/* 16 Scenarios */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] lg:col-span-2">
          <h3 className="text-sm font-medium mb-4">工信部 16 场景评测等级</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={scenarioData} layout="vertical" margin={{ left: 70 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" domain={[0, 3]} ticks={[0, 1, 2, 3]} tick={{ fontSize: 11 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={65} />
              <Tooltip formatter={(v) => [`${v}级`, '等级']} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {scenarioData.map((entry, i) => (
                  <Cell key={i} fill={entry.score >= 3 ? '#22c55e' : entry.score >= 2 ? '#f59e0b' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
