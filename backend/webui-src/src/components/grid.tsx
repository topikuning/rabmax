import { AgGridReact } from 'ag-grid-react';
import {
  AllCommunityModule, ModuleRegistry, themeQuartz,
  type ColDef, type GridReadyEvent, type GridOptions,
} from 'ag-grid-community';

ModuleRegistry.registerModules([AllCommunityModule]);

// Tema Quartz, warna terikat CSS var → otomatis ikut light/dark.
export const boqTheme = themeQuartz.withParams({
  accentColor: 'var(--ag-accent)',
  backgroundColor: 'var(--ag-bg)',
  foregroundColor: 'var(--ag-fg)',
  borderColor: 'var(--ag-border)',
  headerBackgroundColor: 'var(--ag-header)',
  rowHoverColor: 'var(--ag-hover)',
  selectedRowBackgroundColor: 'var(--ag-selected)',
  headerFontWeight: 600,
  fontFamily: 'inherit',
  fontSize: 13,
  headerHeight: 42,
  rowHeight: 40,
  wrapperBorderRadius: 12,
});

interface DataGridProps<T> {
  rowData: T[];
  columnDefs: ColDef<T>[];
  quickFilter?: string;
  getRowId?: (p: { data: T }) => string;
  onGridReady?: (e: GridReadyEvent) => void;
  options?: GridOptions<T>;
  pageSize?: number;
}

export function DataGrid<T>({
  rowData, columnDefs, quickFilter, getRowId, onGridReady, options, pageSize = 50,
}: DataGridProps<T>) {
  return (
    <div className="flex-1 min-h-0">
      <AgGridReact<T>
        theme={boqTheme}
        rowData={rowData}
        columnDefs={columnDefs}
        defaultColDef={{ sortable: true, filter: true, resizable: true, flex: 1, minWidth: 90 }}
        quickFilterText={quickFilter}
        getRowId={getRowId ? (p) => getRowId({ data: p.data }) : undefined}
        onGridReady={onGridReady}
        animateRows
        pagination
        paginationPageSize={pageSize}
        paginationPageSizeSelector={[25, 50, 100, 200]}
        rowSelection={{ mode: 'singleRow', checkboxes: false, enableClickSelection: true }}
        suppressCellFocus={false}
        {...options}
      />
    </div>
  );
}

export type { ColDef };
