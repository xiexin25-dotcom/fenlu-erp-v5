import { useNavigate, useLocation } from 'react-router-dom';
import { FileText, Users, ShieldCheck } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

interface ModuleItem { title: string; desc: string; path: string; }

const sections: Record<string, { icon: typeof FileText; title: string; items: ModuleItem[] }> = {
  '/mgmt/finance': {
    icon: FileText, title: '财务管理',
    items: [
      { title: '总账科目', desc: 'GL 科目树', path: '/mgmt/finance/accounts' },
      { title: '记账凭证', desc: '借贷平衡校验', path: '/mgmt/finance/journal' },
      { title: '应付 / 应收', desc: 'AP / AR 管理', path: '/mgmt/finance/apar' },
    ],
  },
  '/mgmt/hr': {
    icon: Users, title: '人力资源',
    items: [
      { title: '员工管理', desc: '花名册', path: '/mgmt/hr/employees' },
      { title: '考勤管理', desc: '打卡 + 加班', path: '/mgmt/hr/attendance' },
      { title: '薪资管理', desc: '月度工资条', path: '/mgmt/hr/payroll' },
    ],
  },
  '/mgmt/approval': {
    icon: ShieldCheck, title: '审批中心',
    items: [
      { title: '审批记录', desc: '历史查询', path: '/mgmt/approval/list' },
    ],
  },
};

export default function MgmtPage() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const section = sections[pathname] || sections['/mgmt/finance'];
  const Icon = section.icon;

  return (
    <div className="p-6">
      <PageHeader title={section.title} icon={<Icon className="text-indigo-500" size={24} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {section.items.map(item => (
          <div key={item.title} onClick={() => navigate(item.path)}
            className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] cursor-pointer hover:shadow-md hover:border-indigo-300 transition">
            <h3 className="font-medium">{item.title}</h3>
            <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
