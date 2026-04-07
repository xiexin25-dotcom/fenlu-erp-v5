import { useQuery } from '@tanstack/react-query';
import { Clock } from 'lucide-react';
import { mgmtApi, type Attendance } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

const columns: Column<Attendance>[] = [
  { key: 'employee_id', header: '员工', render: r => (r.employee_id || '').slice(0, 8), className: 'font-mono' },
  { key: 'work_date', header: '日期', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.work_date as string | undefined;
    return val ? val.slice(0, 10) : '—';
  }},
  { key: 'clock_in', header: '签到', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.clock_in as string | undefined;
    return val ? val.slice(11, 16) : '—';
  }},
  { key: 'clock_out', header: '签退', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.clock_out as string | undefined;
    return val ? val.slice(11, 16) : '—';
  }},
  { key: 'work_hours', header: '工时(h)', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    return (rec.work_hours as number) ?? '—';
  }},
  { key: 'overtime_hours', header: '加班(h)', className: 'text-right', render: r => {
    const rec = r as unknown as Record<string, unknown>;
    const val = rec.overtime_hours as number | undefined;
    return val && val > 0 ? <span className="text-amber-600">{val}</span> : '0';
  }},
  { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
];

export default function AttendanceList() {
  const { data, isLoading } = useQuery({ queryKey: ['attendance'], queryFn: () => mgmtApi.listAttendance() });
  return (
    <div className="p-6">
      <PageHeader title="考勤管理" subtitle="打卡 + 加班" icon={<Clock className="text-indigo-500" size={24} />} />
      <DataTable<Attendance> columns={columns} data={data || []} loading={isLoading} emptyText="暂无考勤记录" />
    </div>
  );
}
