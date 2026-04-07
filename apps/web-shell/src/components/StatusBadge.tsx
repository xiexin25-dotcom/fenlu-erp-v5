const colorMap: Record<string, [string, string]> = {
  // [bg, fg] — muted Apple-style pastels
  planned: ['var(--status-gray)', 'var(--status-gray-fg)'],
  draft: ['var(--status-gray)', 'var(--status-gray-fg)'],
  closed: ['var(--status-gray)', 'var(--status-gray-fg)'],
  inactive: ['var(--status-gray)', 'var(--status-gray-fg)'],

  released: ['var(--status-blue)', 'var(--status-blue-fg)'],
  reviewing: ['var(--status-blue)', 'var(--status-blue-fg)'],
  preferred: ['var(--status-blue)', 'var(--status-blue-fg)'],

  in_progress: ['var(--status-amber)', 'var(--status-amber-fg)'],
  pending: ['var(--status-amber)', 'var(--status-amber-fg)'],
  conditional: ['var(--status-amber)', 'var(--status-amber-fg)'],
  assigned: ['var(--status-amber)', 'var(--status-amber-fg)'],
  rectifying: ['var(--status-amber)', 'var(--status-amber-fg)'],
  partial: ['var(--status-amber)', 'var(--status-amber-fg)'],

  completed: ['var(--status-green)', 'var(--status-green-fg)'],
  approved: ['var(--status-green)', 'var(--status-green-fg)'],
  active: ['var(--status-green)', 'var(--status-green-fg)'],
  pass: ['var(--status-green)', 'var(--status-green-fg)'],
  verified: ['var(--status-green)', 'var(--status-green-fg)'],
  posted: ['var(--status-green)', 'var(--status-green-fg)'],
  paid: ['var(--status-green)', 'var(--status-green-fg)'],

  reported: ['var(--status-red)', 'var(--status-red-fg)'],
  fail: ['var(--status-red)', 'var(--status-red-fg)'],
  overdue: ['var(--status-red)', 'var(--status-red-fg)'],
  blacklisted: ['var(--status-red)', 'var(--status-red-fg)'],

  effective: ['var(--status-purple)', 'var(--status-purple-fg)'],
  strategic: ['var(--status-purple)', 'var(--status-purple-fg)'],
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
  if (!status) return null;
  const s = status.toLowerCase();
  const [bg, fg] = colorMap[s] || ['var(--status-gray)', 'var(--status-gray-fg)'];
  const label = labelMap[s] || status;
  return (
    <span
      className="inline-flex items-center px-2 py-[3px] rounded-md text-[11px] font-medium"
      style={{ background: bg, color: fg }}
    >
      {label}
    </span>
  );
}
