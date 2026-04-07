import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScrollText } from 'lucide-react';
import { api } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';

interface AuditLog {
  id: string; user_id: string | null; username: string | null;
  method: string; path: string; status_code: number;
  resource: string | null; action: string | null; detail: string | null;
  ip_address: string | null; created_at: string | null;
}

const resourceLabels: Record<string, string> = {
  'plm.product': '产品', 'plm.customer': '客户', 'plm.ecn': 'ECN变更',
  'plm.ticket': '售后工单', 'plm.bom': 'BOM', 'plm.routing': '工艺路线',
  'plm.lead': '销售线索', 'plm.opportunity': '商机', 'plm.quote': '报价单',
  'mfg.work_order': '生产工单', 'mfg.job_ticket': '报工', 'mfg.qc_inspection': '质检',
  'mfg.safety_hazard': '安全隐患', 'mfg.equipment': '设备', 'mfg.energy': '能耗',
  'scm.supplier': '供应商', 'scm.purchase_order': '采购单', 'scm.receipt': '收货',
  'scm.warehouse': '仓库', 'scm.stocktake': '盘点', 'scm.inventory': '库存',
  'mgmt.gl_account': 'GL科目', 'mgmt.journal': '凭证', 'mgmt.ap': '应付',
  'mgmt.ar': '应收', 'mgmt.employee': '员工', 'mgmt.attendance': '考勤',
  'mgmt.payroll': '工资', 'mgmt.approval': '审批', 'mgmt.approval_def': '审批流',
  'auth.user': '用户', 'auth.role': '角色',
  'sales.order': '销售订单',
};

const actionLabels: Record<string, string> = {
  create: '新建', update: '修改', delete: '删除', transition: '状态变更',
  close: '关闭', report: '报工', post: '过账', run: '运行',
  receive: '入库', issue: '出库', submit: '提交', action: '审批操作',
  confirm: '确认', payment: '收款', ship: '发货',
};

const methodColors: Record<string, string> = {
  POST: 'var(--status-green-fg)', PATCH: 'var(--status-amber-fg)',
  PUT: 'var(--status-blue-fg)', DELETE: 'var(--status-red-fg)',
};

export default function AuditLogList() {
  const [page, setPage] = useState(1);
  const pageSize = 30;

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', page],
    queryFn: () => api.get<AuditLog[]>(`/auth/audit-logs?skip=${(page - 1) * pageSize}&limit=${pageSize}`),
  });

  const columns: Column<AuditLog>[] = [
    { key: 'created_at', header: '时间', render: r => {
      if (!r.created_at) return '—';
      return new Date(r.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }},
    { key: 'username', header: '操作员', render: r => r.username || '系统' },
    { key: 'method', header: '方法', render: r =>
      <span className="text-[11px] font-mono font-medium" style={{ color: methodColors[r.method] || 'var(--fg)' }}>{r.method}</span>
    },
    { key: 'resource', header: '模块', render: r => resourceLabels[r.resource || ''] || r.resource || '—' },
    { key: 'action', header: '操作', render: r => actionLabels[r.action || ''] || r.action || '—' },
    { key: 'detail', header: '详情', render: r => r.detail
      ? <span className="text-[11px]" style={{ color: 'var(--fg-secondary)' }}>{r.detail}</span>
      : <span style={{ color: 'var(--fg-tertiary)' }}>—</span>
    },
    { key: 'status_code', header: '结果', render: r =>
      <span className="text-[11px] font-mono" style={{ color: r.status_code < 400 ? 'var(--status-green-fg)' : 'var(--status-red-fg)' }}>{r.status_code < 400 ? '成功' : '失败'}</span>
    },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="操作日志" subtitle="所有写操作留痕 · 不可篡改" icon={<ScrollText size={22} strokeWidth={1.5} />} />
      <DataTable<AuditLog>
        columns={columns}
        data={data || []}
        loading={isLoading}
        page={page}
        pageSize={pageSize}
        total={data?.length === pageSize ? page * pageSize + 1 : (page - 1) * pageSize + (data?.length || 0)}
        onPageChange={setPage}
      />
    </div>
  );
}
