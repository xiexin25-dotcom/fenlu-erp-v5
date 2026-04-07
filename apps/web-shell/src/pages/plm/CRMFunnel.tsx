import { useQuery } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import PageHeader from '@/components/PageHeader';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface FunnelData { stage: string; count: number; }

const stageLabels: Record<string, string> = {
  new: '新线索', contacted: '已联系', qualified: '已验证',
  proposal: '方案中', negotiation: '谈判中', won: '已成交', lost: '已流失',
};
const COLORS = ['#94a3b8', '#60a5fa', '#38bdf8', '#818cf8', '#a78bfa', '#22c55e', '#ef4444'];

export default function CRMFunnel() {
  const { data } = useQuery({
    queryKey: ['crm-funnel'],
    queryFn: () => api.get<FunnelData[]>('/plm/crm/funnel'),
    retry: false,
  });

  const chartData = (data || []).map(d => ({ ...d, label: stageLabels[d.stage] || d.stage }));

  return (
    <div className="p-6">
      <PageHeader title="商机漏斗" subtitle="CRM Funnel" icon={<TrendingUp className="text-blue-500" size={24} />} />
      <div className="bg-white rounded-xl p-6 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis dataKey="label" type="category" tick={{ fontSize: 13 }} width={75} />
              <Tooltip formatter={(v) => [`${v} 条`, '数量']} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={28}>
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center py-16 text-[hsl(215.4,16.3%,46.9%)]">
            <p className="text-lg mb-2">暂无商机数据</p>
            <p className="text-sm">通过 API 创建 Lead/Opportunity 后，漏斗图将自动更新</p>
          </div>
        )}
      </div>
    </div>
  );
}
