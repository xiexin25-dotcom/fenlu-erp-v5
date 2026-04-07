import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Factory } from 'lucide-react';
export default function MfgPage() {
    return (_jsxs("div", { className: "p-6", children: [_jsxs("div", { className: "flex items-center gap-3 mb-6", children: [_jsx(Factory, { className: "text-green-500", size: 24 }), _jsx("h1", { className: "text-xl font-bold", children: "\u751F\u4EA7\u5236\u9020\u7BA1\u7406" })] }), _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4", children: [
                    { title: '生产工单', desc: 'MES 生产管控' },
                    { title: '工序报工', desc: 'Job Ticket 报工' },
                    { title: '质量检验', desc: 'QC / SPC 控制图' },
                    { title: '设备管理', desc: 'EAM + OEE' },
                    { title: '安全生产', desc: '隐患闭环管理' },
                    { title: '能耗监控', desc: '单耗分析' },
                    { title: 'APS 排产', desc: 'FIFO + 产能' },
                ].map(item => (_jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] hover:shadow-md transition cursor-pointer", children: [_jsx("h3", { className: "font-medium", children: item.title }), _jsx("p", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1", children: item.desc })] }, item.title))) })] }));
}
