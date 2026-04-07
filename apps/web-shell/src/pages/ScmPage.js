import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Truck } from 'lucide-react';
export default function ScmPage() {
    return (_jsxs("div", { className: "p-6", children: [_jsxs("div", { className: "flex items-center gap-3 mb-6", children: [_jsx(Truck, { className: "text-orange-500", size: 24 }), _jsx("h1", { className: "text-xl font-bold", children: "\u4F9B\u5E94\u94FE\u7BA1\u7406" })] }), _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4", children: [
                    { title: '供应商管理', desc: '评级 + Tier 转换' },
                    { title: '采购管理', desc: 'PR→RFQ→PO→Receipt' },
                    { title: '仓库管理', desc: '多仓 + 4级库位' },
                    { title: '库存管理', desc: 'StockMove 全追溯' },
                    { title: '盘点管理', desc: '差异自动调整' },
                    { title: 'V4 数据迁移', desc: 'ETL + 对账' },
                ].map(item => (_jsxs("div", { className: "bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)] hover:shadow-md transition cursor-pointer", children: [_jsx("h3", { className: "font-medium", children: item.title }), _jsx("p", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1", children: item.desc })] }, item.title))) })] }));
}
