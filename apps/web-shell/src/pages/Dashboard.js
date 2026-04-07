import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from '@tanstack/react-query';
import { dashboardApi, kpiApi } from '@/lib/api';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, } from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, Zap, DollarSign, Activity } from 'lucide-react';
function StatCard({ title, value, unit, icon: Icon, trend, color }) {
    return (_jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]", children: [_jsxs("div", { className: "flex items-center justify-between mb-3", children: [_jsx("span", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)]", children: title }), _jsx("div", { className: `w-9 h-9 rounded-lg flex items-center justify-center ${color}`, children: _jsx(Icon, { size: 18, className: "text-white" }) })] }), _jsxs("div", { className: "flex items-end gap-1", children: [_jsx("span", { className: "text-2xl font-bold", children: value }), unit && _jsx("span", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)] mb-0.5", children: unit })] }), trend && (_jsxs("div", { className: `flex items-center gap-1 mt-1 text-xs ${trend === 'up' ? 'text-green-600' : 'text-red-500'}`, children: [trend === 'up' ? _jsx(TrendingUp, { size: 12 }) : _jsx(TrendingDown, { size: 12 }), _jsxs("span", { children: [trend === 'up' ? '+5.2%' : '-2.1%', " vs last week"] })] }))] }));
}
const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
function KPIGauge({ kpi }) {
    const pct = Math.min(100, Math.round((kpi.current_value / kpi.target_value) * 100));
    const color = pct >= 90 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#ef4444';
    return (_jsx("div", { className: "flex items-center gap-3 py-2", children: _jsxs("div", { className: "flex-1 min-w-0", children: [_jsxs("div", { className: "flex items-center justify-between mb-1", children: [_jsx("span", { className: "text-sm truncate", children: kpi.name }), _jsxs("span", { className: "text-xs text-[hsl(215.4,16.3%,46.9%)]", children: [pct, "%"] })] }), _jsx("div", { className: "h-2 bg-[hsl(210,40%,96.1%)] rounded-full overflow-hidden", children: _jsx("div", { className: "h-full rounded-full transition-all", style: { width: `${pct}%`, background: color } }) })] }) }));
}
// Mock data for when API is unavailable
const mockDashboard = {
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
const mockKPIs = [
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
        placeholderData: mockDashboard, retry: false,
    });
    const { data: kpis } = useQuery({
        queryKey: ['kpis'], queryFn: kpiApi.list,
        placeholderData: mockKPIs, retry: false,
    });
    const d = dashboard ?? mockDashboard;
    const k = kpis ?? mockKPIs;
    return (_jsxs("div", { className: "p-6 space-y-6", children: [_jsxs("div", { className: "flex items-center justify-between", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-xl font-bold", children: "\u9886\u5BFC\u9A7E\u9A76\u8231" }), _jsx("p", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)]", children: "\u51B3\u7B56\u652F\u6301 - \u4E09\u7EA7\u96C6\u6210\u7EA7" })] }), _jsx("span", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)]", children: new Date().toLocaleDateString('zh-CN') })] }), _jsxs("div", { className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4", children: [_jsx(StatCard, { title: "\u4ECA\u65E5\u8425\u6536", value: (d.today_revenue / 10000).toFixed(1), unit: "\u4E07\u5143", icon: DollarSign, trend: "up", color: "bg-blue-500" }), _jsx(StatCard, { title: "\u672C\u5468\u4EA7\u91CF", value: d.weekly_output.toLocaleString(), unit: "\u4EF6", icon: Activity, trend: "up", color: "bg-green-500" }), _jsx(StatCard, { title: "OEE", value: d.weekly_oee.toFixed(1), unit: "%", icon: TrendingUp, trend: "up", color: "bg-purple-500" }), _jsx(StatCard, { title: "\u5B89\u5168\u9690\u60A3", value: d.open_safety_hazards, unit: "\u9879", icon: AlertTriangle, color: "bg-red-500" }), _jsx(StatCard, { title: "\u5355\u8017", value: d.energy_unit_consumption.toFixed(2), unit: "kWh/\u4EF6", icon: Zap, trend: "down", color: "bg-amber-500" }), _jsx(StatCard, { title: "\u73B0\u91D1\u5934\u5BF8", value: (d.cash_position / 10000).toFixed(0), unit: "\u4E07\u5143", icon: DollarSign, color: "bg-cyan-500" })] }), _jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-2 gap-6", children: [_jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]", children: [_jsx("h3", { className: "text-sm font-medium mb-4", children: "\u8425\u6536\u8D8B\u52BF (\u8FD17\u65E5)" }), _jsx(ResponsiveContainer, { width: "100%", height: 240, children: _jsxs(BarChart, { data: d.revenue_trend, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: "#f0f0f0" }), _jsx(XAxis, { dataKey: "date", tick: { fontSize: 12 } }), _jsx(YAxis, { tick: { fontSize: 12 }, tickFormatter: v => `${(v / 10000).toFixed(0)}万` }), _jsx(Tooltip, { formatter: (v) => [`${(Number(v) / 10000).toFixed(1)}万元`, '营收'] }), _jsx(Bar, { dataKey: "amount", fill: "#3b82f6", radius: [4, 4, 0, 0] })] }) })] }), _jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]", children: [_jsx("h3", { className: "text-sm font-medium mb-4", children: "OEE \u8D8B\u52BF (\u8FD17\u65E5)" }), _jsx(ResponsiveContainer, { width: "100%", height: 240, children: _jsxs(LineChart, { data: d.oee_trend, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: "#f0f0f0" }), _jsx(XAxis, { dataKey: "date", tick: { fontSize: 12 } }), _jsx(YAxis, { domain: [80, 95], tick: { fontSize: 12 }, tickFormatter: v => `${v}%` }), _jsx(Tooltip, { formatter: (v) => [`${v}%`, 'OEE'] }), _jsx(Line, { type: "monotone", dataKey: "oee", stroke: "#8b5cf6", strokeWidth: 2, dot: { r: 4 } })] }) })] })] }), _jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-3 gap-6", children: [_jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]", children: [_jsx("h3", { className: "text-sm font-medium mb-3", children: "KPI \u8FBE\u6210\u7387" }), _jsx("div", { className: "space-y-1", children: k.map(kpi => _jsx(KPIGauge, { kpi: kpi }, kpi.code)) })] }), _jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] lg:col-span-2", children: [_jsx("h3", { className: "text-sm font-medium mb-4", children: "\u5DE5\u4FE1\u90E8 16 \u573A\u666F\u8BC4\u6D4B\u7B49\u7EA7" }), _jsx(ResponsiveContainer, { width: "100%", height: 240, children: _jsxs(BarChart, { data: scenarioData, layout: "vertical", margin: { left: 70 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: "#f0f0f0" }), _jsx(XAxis, { type: "number", domain: [0, 3], ticks: [0, 1, 2, 3], tick: { fontSize: 11 } }), _jsx(YAxis, { dataKey: "name", type: "category", tick: { fontSize: 11 }, width: 65 }), _jsx(Tooltip, { formatter: (v) => [`${v}级`, '等级'] }), _jsx(Bar, { dataKey: "score", radius: [0, 4, 4, 0], children: scenarioData.map((entry, i) => (_jsx(Cell, { fill: entry.score >= 3 ? '#22c55e' : entry.score >= 2 ? '#f59e0b' : '#ef4444' }, i))) })] }) })] })] })] }));
}
