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
    <div className="bg-white rounded-xl shadow-sm border border-[hsl(214.3,31.8%,91.4%)] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[hsl(214.3,31.8%,91.4%)] bg-[hsl(210,40%,98%)]">
              {columns.map(col => (
                <th key={col.key} className={`px-4 py-3 text-left font-medium text-[hsl(215.4,16.3%,46.9%)] ${col.className || ''}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length} className="px-4 py-12 text-center">
                <Loader2 className="animate-spin mx-auto text-[hsl(215.4,16.3%,46.9%)]" size={24} />
              </td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={columns.length} className="px-4 py-12 text-center text-[hsl(215.4,16.3%,46.9%)]">{emptyText}</td></tr>
            ) : data.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(row)}
                className={`border-b border-[hsl(214.3,31.8%,91.4%)] last:border-0 ${onRowClick ? 'cursor-pointer hover:bg-[hsl(210,40%,98%)]' : ''} transition`}
              >
                {columns.map(col => (
                  <td key={col.key} className={`px-4 py-3 ${col.className || ''}`}>
                    {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total !== undefined && total > pageSize && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-[hsl(214.3,31.8%,91.4%)]">
          <span className="text-xs text-[hsl(215.4,16.3%,46.9%)]">共 {total} 条</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange?.(page - 1)} disabled={page <= 1}
              className="p-1.5 rounded hover:bg-[hsl(210,40%,96.1%)] disabled:opacity-30 transition"
            ><ChevronLeft size={16} /></button>
            <span className="text-sm">{page} / {totalPages}</span>
            <button
              onClick={() => onPageChange?.(page + 1)} disabled={page >= totalPages}
              className="p-1.5 rounded hover:bg-[hsl(210,40%,96.1%)] disabled:opacity-30 transition"
            ><ChevronRight size={16} /></button>
          </div>
        </div>
      )}
    </div>
  );
}
