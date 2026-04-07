import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Package } from 'lucide-react';
export default function PlmPage() {
    return (_jsxs("div", { className: "p-6", children: [_jsxs("div", { className: "flex items-center gap-3 mb-6", children: [_jsx(Package, { className: "text-blue-500", size: 24 }), _jsx("h1", { className: "text-xl font-bold", children: "\u4EA7\u54C1\u751F\u547D\u5468\u671F\u7BA1\u7406" })] }), _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4", children: [
                    { title: '产品主数据', desc: 'Product + BOM + Routing', count: '—' },
                    { title: 'CAD 文件管理', desc: 'MinIO 存储', count: '—' },
                    { title: 'ECN 工程变更', desc: '变更审批流程', count: '—' },
                    { title: 'CRM 客户管理', desc: 'Customer 360', count: '—' },
                    { title: '商机漏斗', desc: 'Lead → Opportunity → Order', count: '—' },
                    { title: '售后工单', desc: 'SLA + NPS', count: '—' },
                ].map(item => (_jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] hover:shadow-md transition cursor-pointer", children: [_jsx("h3", { className: "font-medium", children: item.title }), _jsx("p", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1", children: item.desc })] }, item.title))) })] }));
}
