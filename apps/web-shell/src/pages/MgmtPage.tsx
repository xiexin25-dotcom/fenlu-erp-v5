import { FileText, Users, BarChart3, ShieldCheck } from 'lucide-react';
import { useLocation } from 'react-router-dom';

const sections: Record<string, { icon: typeof FileText; title: string; items: { title: string; desc: string }[] }> = {
  '/mgmt/finance': {
    icon: FileText, title: '财务管理',
    items: [
      { title: '总账科目', desc: 'GL 科目树' },
      { title: '记账凭证', desc: '借贷平衡校验' },
      { title: '应付账款', desc: 'AP 管理' },
      { title: '应收账款', desc: 'AR 管理' },
      { title: '三张报表', desc: '资产负债表 / 利润表 / 现金流量表' },
    ],
  },
  '/mgmt/hr': {
    icon: Users, title: '人力资源',
    items: [
      { title: '员工管理', desc: '花名册' },
      { title: '考勤管理', desc: '打卡 + 加班' },
      { title: '薪资管理', desc: '月度工资条' },
    ],
  },
  '/mgmt/kpi': {
    icon: BarChart3, title: 'KPI 看板',
    items: [
      { title: 'KPI 定义', desc: '20+ 指标覆盖 16 场景' },
      { title: '数据点管理', desc: '时序数据查询' },
      { title: '趋势分析', desc: '同比/环比' },
    ],
  },
  '/mgmt/approval': {
    icon: ShieldCheck, title: '审批中心',
    items: [
      { title: '审批流定义', desc: '可配置 N-step' },
      { title: '我的待审', desc: '待办事项' },
      { title: '审批记录', desc: '历史查询' },
    ],
  },
};

export default function MgmtPage() {
  const { pathname } = useLocation();
  const section = sections[pathname] || sections['/mgmt/finance'];
  const Icon = section.icon;

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Icon className="text-indigo-500" size={24} />
        <h1 className="text-xl font-bold">{section.title}</h1>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {section.items.map(item => (
          <div key={item.title} className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] hover:shadow-md transition cursor-pointer">
            <h3 className="font-medium">{item.title}</h3>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
