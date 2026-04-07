import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onRowClick?: (row: T) => void;
  emptyText?: string;
}

export default function DataTable<T extends object>({
  columns, data, loading, page = 1, pageSize = 20, total, onPageChange, onRowClick, emptyText = '暂无数据',
}: Props<T>) {
  const totalPages = total ? Math.ceil(total / pageSize) : 1;

  return (
    <div className="overflow-hidden" style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--divider)' }}>
              {columns.map(col => (
                <th key={col.key} className={`px-5 py-3 text-left text-[12px] font-medium uppercase tracking-wider ${col.className || ''}`} style={{ color: 'var(--fg-tertiary)' }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length} className="px-5 py-16 text-center">
                <Loader2 className="animate-spin mx-auto" size={20} style={{ color: 'var(--fg-tertiary)' }} />
              </td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={columns.length} className="px-5 py-16 text-center text-[13px]" style={{ color: 'var(--fg-tertiary)' }}>{emptyText}</td></tr>
            ) : data.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(row)}
                className={onRowClick ? 'cursor-pointer' : ''}
                style={{ borderBottom: i < data.length - 1 ? '1px solid var(--divider)' : 'none' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {columns.map(col => (
                  <td key={col.key} className={`px-5 py-3.5 ${col.className || ''}`}>
                    {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total !== undefined && total > pageSize && (
        <div className="flex items-center justify-between px-5 py-3" style={{ borderTop: '1px solid var(--divider)' }}>
          <span className="text-[12px]" style={{ color: 'var(--fg-tertiary)' }}>共 {total} 条</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange?.(page - 1)} disabled={page <= 1}
              className="p-1.5 rounded-lg disabled:opacity-20"
              style={{ color: 'var(--fg-secondary)' }}
            ><ChevronLeft size={15} /></button>
            <span className="text-[12px] px-2" style={{ color: 'var(--fg-secondary)' }}>{page} / {totalPages}</span>
            <button
              onClick={() => onPageChange?.(page + 1)} disabled={page >= totalPages}
              className="p-1.5 rounded-lg disabled:opacity-20"
              style={{ color: 'var(--fg-secondary)' }}
            ><ChevronRight size={15} /></button>
          </div>
        </div>
      )}
    </div>
  );
}
