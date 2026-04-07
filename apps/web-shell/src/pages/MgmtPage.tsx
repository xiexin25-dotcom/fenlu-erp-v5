import { useLocation } from 'react-router-dom';
import { FileText, Users, ShieldCheck } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import ModuleCard from '@/components/ModuleCard';

const sections: Record<string, { icon: typeof FileText; title: string; subtitle: string; items: { title: string; desc: string; path: string }[] }> = {
  '/mgmt/finance': {
    icon: FileText, title: '财务管理', subtitle: 'Financial Management',
    items: [
      { title: '总账科目', desc: 'GL 科目树', path: '/mgmt/finance/accounts' },
      { title: '记账凭证', desc: '借贷平衡校验', path: '/mgmt/finance/journal' },
      { title: '应付 / 应收', desc: 'AP / AR 管理', path: '/mgmt/finance/apar' },
      { title: '财务三表', desc: '资产负债表 / 利润表 / 现金流量表', path: '/mgmt/finance/statements' },
    ],
  },
  '/mgmt/hr': {
    icon: Users, title: '人力资源', subtitle: 'Human Resources',
    items: [
      { title: '员工管理', desc: '花名册', path: '/mgmt/hr/employees' },
      { title: '考勤管理', desc: '打卡 + 加班', path: '/mgmt/hr/attendance' },
      { title: '薪资管理', desc: '月度工资条', path: '/mgmt/hr/payroll' },
    ],
  },
  '/mgmt/approval': {
    icon: ShieldCheck, title: '审批中心', subtitle: 'Approval Center',
    items: [
      { title: '审批记录', desc: '历史查询', path: '/mgmt/approval/list' },
    ],
  },
};

export default function MgmtPage() {
  const { pathname } = useLocation();
  const section = sections[pathname] || sections['/mgmt/finance'];
  const Icon = section.icon;

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title={section.title} subtitle={section.subtitle} icon={<Icon size={22} strokeWidth={1.5} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {section.items.map(m => <ModuleCard key={m.title} {...m} />)}
      </div>
    </div>
  );
}
