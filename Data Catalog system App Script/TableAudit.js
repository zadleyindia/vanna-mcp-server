/**************************************************************
 * TABLE AUDIT – paginated, include_raw flag, full metadata
 * Also updates BigQuery table/view descriptions from the sheet.
 **************************************************************/
function syncTables() {

  const ss       = SpreadsheetApp.getActiveSpreadsheet();
  const dsSheet  = ss.getSheetByName('Datasets');
  const tblSheet = ss.getSheetByName('Table_Metadata');
  const bq       = BigQuery;

  /* 1 ▪ active datasets with include_raw? flag (column 13) */
  const dsRows = dsSheet.getRange(2, 1, dsSheet.getLastRow() - 1, 13).getValues();
  const datasets = dsRows
        .filter(r => r[11] === 'In Use')                 // status
        .map(r => ({
          proj      : r[0],
          ds        : r[1],
          domain    : r[3],
          includeRaw: (r[12] || '').toString().toUpperCase() === 'YES'
        }));

  if (!datasets.length) return;

  /* 2 ▪ index existing table rows + reset exists_flag */
  const map = new Map();                                 // fqdn → sheetRow
  if (tblSheet.getLastRow() > 1) {
    tblSheet.getRange(2, 1, tblSheet.getLastRow() - 1, 14)
            .getValues()
            .forEach((row, i) => {
              if (row[3]) map.set(row[3], i + 2);
              tblSheet.getRange(i + 2, 14).setValue(false);   // exists_flag FALSE
            });
  }

  /* 3 ▪ iterate datasets with pagination */
  datasets.forEach(d => {

    let token = null;
    do {
      const resp = bq.Tables.list(d.proj, d.ds, { maxResults: 1000, pageToken: token });
      (resp.tables || []).forEach(tStub => {

        const id = tStub.tableReference.tableId;
        if (!d.includeRaw && id.startsWith('sql_')) return;   // skip raw tables if flagged

        /* full metadata call */
        const tMeta = bq.Tables.get(d.proj, d.ds, id);

        const fqdn   = `${d.proj}.${d.ds}.${id}`;
        const isView = (tMeta.type === 'VIEW');
        const rows   = Number(tMeta.numRows || 0);
        const cols   = tMeta.schema?.fields?.length || 0;
        const updMs  = Number(tMeta.lastModifiedTime || 0);
        const updTs  = updMs ? new Date(updMs) : '';

        if (map.has(fqdn)) {                  /* UPDATE */
          const r = map.get(fqdn);

          const lastAudit = tblSheet.getRange(r, 11).getValue(); // column_profile_last_audit
          const due = (!lastAudit || (updMs && updMs > lastAudit.getTime()));

          tblSheet.getRange(r, 5).setValue(isView ? 'VIEW' : 'TABLE');
          tblSheet.getRange(r, 8).setValue(rows);
          tblSheet.getRange(r, 9).setValue(cols);
          tblSheet.getRange(r,10).setValue(updTs)
                   .setNumberFormat(updTs ? 'yyyy-MM-dd HH:mm:ss' : '');
          tblSheet.getRange(r,12).setValue(due);          // column_profile_due
          tblSheet.getRange(r,14).setValue(true);         // exists_flag

          // 🟩 Update BigQuery table/view description to match grain_description (col 7)
          try {
            const sheetDesc = tblSheet.getRange(r, 7).getValue() || '';
            const tableMeta = bq.Tables.get(d.proj, d.ds, id);
            tableMeta.description = sheetDesc;
            bq.Tables.update(tableMeta, d.proj, d.ds, id);
            console.log(`✅ Updated description for ${fqdn}`);
          } catch (e) {
            console.warn(`⚠️ Could not update table/view description for ${fqdn}:`, e);
          }

        } else {                                          /* APPEND */
          tblSheet.appendRow([
            d.proj, d.ds, id, fqdn,
            isView ? 'VIEW' : 'TABLE',
            d.domain, '',
            rows, cols, updTs,
            '',                   // column_profile_last_audit
            true,                 // column_profile_due
            'In Use',
            true                  // exists_flag
          ]);

          // 🟩 Update BigQuery table/view description to blank (default)
          try {
            const tableMeta = bq.Tables.get(d.proj, d.ds, id);
            tableMeta.description = '';
            bq.Tables.update(tableMeta, d.proj, d.ds, id);
            console.log(`✅ Cleared description for new entry ${fqdn}`);
          } catch (e) {
            console.warn(`⚠️ Could not clear description for ${fqdn}:`, e);
          }
        }
      });
      token = resp.nextPageToken;
    } while (token);
  });

  /* 4 ▪ mark tables no longer present */
  const flags = tblSheet.getRange(2, 14, tblSheet.getLastRow() - 1).getValues();
  flags.forEach((f, i) => {
    if (!f[0]) {
      const r = i + 2;
      tblSheet.getRange(r, 5).setValue('DELETED');
      tblSheet.getRange(r,13).setValue('Obsolete');
    }
  });

  console.log('✅ Table sync complete!');
}

/**
 * Fetches SQL queries for views marked as In Use in Table_Metadata
 * and writes them to a separate sheet: View_Definitions.
 * Adds column: view_type = STANDARD or MATERIALIZED
 */
function syncViewQueries() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tblSheet = ss.getSheetByName('Table_Metadata');
  const viewSheetName = 'View_Definitions';
  let viewSheet = ss.getSheetByName(viewSheetName);

  if (!viewSheet) {
    viewSheet = ss.insertSheet(viewSheetName);
  } else {
    viewSheet.clearContents();
  }

  // Set headers in snake_case
  viewSheet.appendRow(['project_id', 'dataset_id', 'view_name', 'sql_query', 'view_type']);

  const bq = BigQuery;

  const lastRow = tblSheet.getLastRow();
  if (lastRow < 2) return;

  const tableRows = tblSheet.getRange(2, 1, lastRow - 1, 14).getValues();

  const inUseViews = tableRows.filter(r =>
    r[4] === 'VIEW' && r[12] === 'In Use'
  ).map(r => ({
    proj: r[0],
    ds: r[1],
    tableId: r[2]
  }));

  if (!inUseViews.length) {
    console.log('✅ No In Use views found in Table_Metadata.');
    return;
  }

  inUseViews.forEach(v => {
    try {
      const viewMeta = bq.Tables.get(v.proj, v.ds, v.tableId);
      const viewQuery = viewMeta.view?.query || '';
      const viewType = viewMeta.materializedView ? 'MATERIALIZED' : 'STANDARD';

      viewSheet.appendRow([
        v.proj,
        v.ds,
        v.tableId,
        viewQuery,
        viewType
      ]);
      console.log(`✅ Retrieved view: ${v.proj}.${v.ds}.${v.tableId}`);
    } catch (e) {
      console.warn(`⚠️ Could not retrieve view query for ${v.proj}.${v.ds}.${v.tableId}:`, e);
    }
  });

  console.log('✅ View queries sync complete!');
}




