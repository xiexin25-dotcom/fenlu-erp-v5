import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Clock } from 'lucide-react';
import { mgmtApi, api, type Attendance } from '@/lib/api';
import DataTable, { type Column } from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';

function num(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v) || 0;
  return 0;
}

function timeStr(v: unknown): string {
  if (!v) return '—';
  const s = String(v);
  // Could be "08:16:00" or "2026-04-07T08:16:00"
  if (s.includes('T')) return s.slice(11, 16);
  return s.slice(0, 5); // "08:16"
}

export default function AttendanceList() {
  const { data, isLoading } = useQuery({ queryKey: ['attendance'], queryFn: () => mgmtApi.listAttendance() });
  const { data: empData } = useQuery({ queryKey: ['employees-all'], queryFn: () => api.get<Array<{ id: string; name: string; employee_no: string }>>('/mgmt/hr/employees') });

  const empMap = useMemo(() => {
    const m: Record<string, string> = {};
    const items = Array.isArray(empData) ? empData : (empData as unknown as { items?: Array<{ id: string; name: string; employee_no: string }> })?.items || [];
    for (const e of items) m[e.id] = `${e.name} (${e.employee_no})`;
    return m;
  }, [empData]);

  const columns: Column<Attendance>[] = [
    { key: 'employee', header: '员工', render: r => empMap[r.employee_id] || r.employee_id?.slice(0, 8) },
    { key: 'work_date', header: '日期', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return String(rec.work_date || '').slice(0, 10);
    }},
    { key: 'clock_in', header: '签到', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return timeStr(rec.clock_in);
    }},
    { key: 'clock_out', header: '签退', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return timeStr(rec.clock_out);
    }},
    { key: 'work_hours', header: '工时(h)', className: 'text-right', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      return num(rec.work_hours).toFixed(1);
    }},
    { key: 'overtime_hours', header: '加班(h)', className: 'text-right', render: r => {
      const rec = r as unknown as Record<string, unknown>;
      const v = num(rec.overtime_hours);
      return v > 0 ? <span style={{ color: 'var(--status-amber-fg)' }}>{v.toFixed(1)}</span> : '0';
    }},
    { key: 'status', header: '状态', render: r => <StatusBadge status={r.status} /> },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="考勤管理" subtitle="打卡 + 加班" icon={<Clock size={22} strokeWidth={1.5} />} />
      <DataTable<Attendance> columns={columns} data={data || []} loading={isLoading} />
    </div>
  );
}
