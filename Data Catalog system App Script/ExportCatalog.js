/**********************************************************************
 * EXPORT CATALOG FROM BIGQUERY → JSON → GOOGLE DRIVE
 * 
 * Source: BigQuery tables in PROJECT.DATASET
 * Includes:
 *   - Datasets (where status = 'In Use')
 *   - Tables (status = 'In Use' and exists_flag = TRUE)
 *   - Columns (where exists_flag = TRUE)
 *   - View Definitions
 *   - Hevo Models
 *
 * Output:
 *   - JSON structure grouped by dataset → tables (with columns, query)
 *   - Query source marked as 'view' or 'hevo'
 *   - File saved to Drive (DRIVE_FOLDER_ID)
 *   - Logs entry in "Exports" sheet
 **********************************************************************/

function exportCatalogJSONFromBQ() {
  const proj = PROJECT;
  const ds = DATASET;
  const folder = DriveApp.getFolderById(DRIVE_FOLDER_ID);

  const datasetsQuery = `SELECT * FROM \`${proj}.${ds}.Datasets\` WHERE status = 'In Use'`;
  const tablesQuery = `SELECT * FROM \`${proj}.${ds}.Table_Metadata\` WHERE status = 'In Use' AND exists_flag = TRUE`;
  const columnsQuery = `SELECT * FROM \`${proj}.${ds}.Column_Metadata\` WHERE exists_flag = TRUE`;
  const viewsQuery = `SELECT project_id, dataset_id, view_name, sql_query, view_type FROM \`${proj}.${ds}.View_Definitions\``;
  const hevoQuery = `SELECT project_id, dataset_id, table_id, source_query FROM \`${proj}.${ds}.Hevo_Models\``;

  const datasetsRows = runBQRows(datasetsQuery);
  const tablesRows = runBQRows(tablesQuery);
  const columnsRows = runBQRows(columnsQuery);
  const viewsRows = runBQRows(viewsQuery);
  const hevoRows = runBQRows(hevoQuery);

  const datasets = {};
  datasetsRows.forEach(row => {
    delete row.status;
    row.tables = [];
    datasets[`${row.project_id}.${row.dataset_id}`] = row;
  });

  const tableMap = {};
  tablesRows.forEach(row => {
    delete row.status;
    delete row.exists_flag;
    row.columns = [];
    row.query = null;
    row.query_source = null;
    const key = `${row.project_id}.${row.dataset_id}`;
    datasets[key]?.tables.push(row);
    tableMap[`${row.project_id}.${row.dataset_id}.${row.table_id}`] = row;
  });

  columnsRows.forEach(col => {
    delete col.exists_flag;
    const key = `${col.project_id}.${col.dataset_id}.${col.table_id}`;
    const table = tableMap[key];
    if (table) table.columns.push(col);
  });

  viewsRows.forEach(v => {
    const key = `${v.project_id}.${v.dataset_id}.${v.view_name}`;
    const table = tableMap[key];
    if (table && !table.query) {
      table.query = v.sql_query;
      table.query_source = 'view';
      table.view_type = (v.view_type || '').toLowerCase();
    }
  });

  hevoRows.forEach(h => {
    const key = `${h.project_id}.${h.dataset_id}.${h.table_id}`;
    const table = tableMap[key];
    if (table && !table.query) {
      table.query = h.source_query;
      table.query_source = 'hevo';
    }
  });

  const result = Object.values(datasets);
  const json = JSON.stringify({ catalog: result }, null, 2);
  const fileName = `CatalogExport_${new Date().toISOString().replace(/[.:]/g, '-')}.json`;
  const file = folder.createFile(fileName, json, MimeType.PLAIN_TEXT);

  let exportSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Exports');
  if (!exportSheet) exportSheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet('Exports');
  if (exportSheet.getLastRow() === 0) {
    exportSheet.appendRow(['Timestamp', 'Export File Link', 'Notes']);
  }
  exportSheet.appendRow([new Date(), file.getUrl(), 'Catalog JSON export (BQ-based, clean)']);

  Logger.log(`✅ Exported to Drive: ${file.getUrl()}`);
  SpreadsheetApp.getUi().alert(`✅ Export complete!\n\nLink: ${file.getUrl()}`);
}

/**
 * Helper to run BigQuery query and return parsed rows
 */
function runBQRows(query) {
  const request = { query, useLegacySql: false };
  const job = BigQuery.Jobs.insert({ configuration: { query: request } }, PROJECT);
  const result = BigQuery.Jobs.getQueryResults(PROJECT, job.jobReference.jobId);
  const fields = result.schema.fields.map(f => f.name);
  return (result.rows || []).map(row => {
    const obj = {};
    row.f.forEach((cell, i) => obj[fields[i]] = cell.v);
    return obj;
  });
}





