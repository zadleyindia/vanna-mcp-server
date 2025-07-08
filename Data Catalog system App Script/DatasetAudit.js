/**
 * DATASET AUDIT – updates row_count_last_audit (J)
 * and last_updated_ts (K) in the “Datasets” sheet.
 * 
 * It fetches all tables for each dataset, sums their row counts,
 * and identifies the most recent update timestamp (max lastModifiedTime).
 * 
 * Requirements:
 * - BigQuery Advanced Service must be enabled.
 */

/**
 * DATASET AUDIT – syncs datasets from BigQuery to the “Datasets” sheet,
 * and updates the dataset description in BigQuery to match the sheet.
 */
function syncDatasets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dsSheet = ss.getSheetByName('Datasets');
  const bq = BigQuery;
  const now = new Date();

  // 1 ▪ Get existing dataset keys (project_id|dataset_id)
  const lastRow = dsSheet.getLastRow();
  const existingKeys = new Set();
  const sheetRows = [];
  if (lastRow > 1) {
    sheetRows.push(...dsSheet.getRange(2, 1, lastRow - 1, 11).getValues());
    sheetRows.forEach(r => existingKeys.add(`${r[0]}|${r[1]}`));
  }

  // 2 ▪ Iterate over projects in the sheet
  const projectIds = [...new Set(sheetRows.map(r => r[0]))];

  projectIds.forEach(proj => {
    let datasets;
    try {
      datasets = bq.Datasets.list(proj).datasets || [];
    } catch (e) {
      console.warn(`⚠️ Failed to list datasets for project: ${proj}`, e);
      return;
    }

    datasets.forEach(ds => {
      const dsId = ds.datasetReference.datasetId;
      const key = `${proj}|${dsId}`;
      const idxRow = sheetRows.findIndex(r => r[0] === proj && r[1] === dsId);
      const sheetRowNum = idxRow + 2;

      let sheetDesc = '';
      if (idxRow !== -1) {
        sheetDesc = sheetRows[idxRow][8] || '';  // Column I = description
      }

      // 🟩 Update BigQuery dataset description
      try {
        const dsMeta = bq.Datasets.get(proj, dsId);
        dsMeta.friendlyName = dsId;  // optional: add friendlyName
        dsMeta.description = sheetDesc;  // 🟢 Update with sheet's description
        bq.Datasets.update(dsMeta, proj, dsId);
      } catch (e) {
        console.warn(`⚠️ Could not update description for ${proj}.${dsId}:`, e);
      }

      // 🟩 Summarize tables (row count and last update)
      let rowCount = 0;
      let lastUpdated = 0;
      try {
        const tablesList = bq.Tables.list(proj, dsId).tables || [];
        rowCount = tablesList.reduce((sum, t) => sum + (Number(t.numRows) || 0), 0);
        lastUpdated = tablesList.reduce((max, t) => {
          const modTime = Number(t.lastModifiedTime || 0);
          return modTime > max ? modTime : max;
        }, 0);
      } catch (e) {
        console.warn(`⚠️ Failed to list tables for ${proj}.${dsId}:`, e);
      }

      const lastUpdatedDate = lastUpdated ? new Date(lastUpdated) : now;

      if (idxRow !== -1) {
        // Update existing row
        dsSheet.getRange(sheetRowNum, 10).setValue(rowCount); // Column J
        dsSheet.getRange(sheetRowNum, 11).setValue(lastUpdatedDate)
          .setNumberFormat('yyyy-MM-dd HH:mm:ss'); // Column K
      } else {
        // Append new dataset entry
        dsSheet.appendRow([
          proj,
          dsId,
          `${proj}.${dsId}`,   // dataset_fqdn
          '', '', '', '', '', '',    // empty business_domain etc.
          rowCount,
          lastUpdatedDate
        ]);
      }
    });
  });

  console.log('✅ Dataset sync and description update complete!');
}
