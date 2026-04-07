const colorMap: Record<string, string> = {
  // work order / general
  planned: 'bg-gray-100 text-gray-700',
  released: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  closed: 'bg-gray-200 text-gray-500',
  // ecn
  draft: 'bg-gray-100 text-gray-700',
  reviewing: 'bg-blue-100 text-blue-700',
  approved: 'bg-green-100 text-green-700',
  effective: 'bg-purple-100 text-purple-700',
  // safety
  reported: 'bg-red-100 text-red-700',
  assigned: 'bg-orange-100 text-orange-700',
  rectifying: 'bg-amber-100 text-amber-700',
  verified: 'bg-green-100 text-green-700',
  // supplier tier
  strategic: 'bg-purple-100 text-purple-700',
  preferred: 'bg-blue-100 text-blue-700',
  blacklisted: 'bg-red-100 text-red-700',
  // finance
  posted: 'bg-green-100 text-green-700',
  pending: 'bg-amber-100 text-amber-700',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
  partial: 'bg-amber-100 text-amber-700',
  // qc
  pass: 'bg-green-100 text-green-700',
  fail: 'bg-red-100 text-red-700',
  conditional: 'bg-amber-100 text-amber-700',
  // generic
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-200 text-gray-500',
};

const labelMap: Record<string, string> = {
  planned: '已计划', released: '已下达', in_progress: '进行中',
  completed: '已完成', closed: '已关闭', draft: '草稿',
  reviewing: '审核中', approved: '已批准', effective: '已生效',
  reported: '已报告', assigned: '已分配', rectifying: '整改中',
  verified: '已验证', strategic: '战略级', preferred: '优选级',
  blacklisted: '黑名单', posted: '已过账', pending: '待处理',
  paid: '已付款', overdue: '逾期', partial: '部分', pass: '合格',
  fail: '不合格', conditional: '有条件', active: '活跃', inactive: '停用',
};

export default function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  const color = colorMap[s] || 'bg-gray-100 text-gray-700';
  const label = labelMap[s] || status;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}
