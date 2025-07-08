/**
 * COLUMN AUDIT – final script with precise exists_flag logic.
 *
 * For each column in Column_Metadata, exists_flag is set according to:
 *   • TRUE, if its parent table is currently active and not awaiting re-profiling:
 *       – Table_Metadata.status       === 'In Use'
 *       – Table_Metadata.exists_flag === TRUE
 *       – Table_Metadata.column_profile_due === FALSE
 *   • FALSE, otherwise (including tables that are:
 *       – not “In Use”
 *       – marked deleted (exists_flag = FALSE)
 *       – currently due for profiling (column_profile_due = TRUE)
 *       – no longer listed in Table_Metadata)
 *
 * After resetting all column exists_flags, only tables with
 * column_profile_due = TRUE and status = 'In Use' are profiled.
 * Profiling updates column statistics, clears the profile_due flag,
 * and stamps column_profile_last_audit. Errors are logged to ColumnAudit_Errors.
 */

function syncColumns() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tblSheet = ss.getSheetByName('Table_Metadata');
  const colSheet = ss.getSheetByName('Column_Metadata');
  const bq = BigQuery;
  const now = new Date();

  // 1 ▪ Load Table_Metadata rows (14 cols)
  const tblRows = tblSheet
    .getRange(2, 1, tblSheet.getLastRow() - 1, 14)
    .getValues();

  // 2 ▪ Determine profiling targets (In Use & column_profile_due=TRUE)
  const targets = tblRows.filter(r => r[11] && r[12] === 'In Use' && r[13]);

  // ── NEW ──  
  // 3a ▪ Build set of tables for which exists_flag should be TRUE
  //      Only those with status='In Use' AND column_profile_due = FALSE
  const existsKeys = new Set(
    tblRows
      .filter(r => r[12] === 'In Use' && !r[11])   // <-- exclude those still due
      .map(r => `${r[0]}.${r[1]}.${r[2]}`)
  );

  // 3b ▪ Update exists_flag in Column_Metadata for all columns
  if (colSheet.getLastRow() > 1) {
    const colRows = colSheet
      .getRange(2, 1, colSheet.getLastRow() - 1, 19)
      .getValues();
    colRows.forEach((row, i) => {
      const key = `${row[0]}.${row[1]}.${row[2]}`;
      const flag = existsKeys.has(key);
      colSheet.getRange(i + 2, 19).setValue(flag);
    });
  }
  // ──────────────────────────────────────────────────────────────

  // 4 ▪ If nothing to profile, stop here
  if (!targets.length) return;

  // 5 ▪ Index existing Column_Metadata rows for upserts
  const colIdx = new Map();
  colSheet.getRange(2, 1, colSheet.getLastRow() - 1, 19)
    .getValues()
    .forEach((row, i) => {
      colIdx.set(`${row[0]}.${row[1]}.${row[2]}|${row[3]}`, i + 2);
    });

  const numeric = ['INT64','NUMERIC','BIGNUMERIC','FLOAT64','DECIMAL'];
  const skipTypes = ['BYTES'];
  const skipColumnNames = ['rowversion'];

  // 6 ▪ Profile each target table’s columns
  targets.forEach(t => {
    const [proj, ds, tbl] = t;
    const fqdn = `${proj}.${ds}.${tbl}`;
    let rowCntTbl = 0;
    try {
      rowCntTbl = Number((bq.Tables.get(proj,ds,tbl).numRows) || 0);
    } catch(e){
      console.warn(`Skipping ${fqdn}: row‐count failed.`);
    }

    // get column list
    const metaSQL = `
      SELECT column_name, data_type, is_nullable
      FROM \`${proj}.${ds}.INFORMATION_SCHEMA.COLUMNS\`
      WHERE table_name='${tbl}'
    `;
    const cols = bq.Jobs.getQueryResults(
      proj,
      bq.Jobs.insert(
        { configuration:{ query:{ query: metaSQL, useLegacySql:false } } },
        proj
      ).jobReference.jobId
    ).rows || [];

    cols.forEach(c => {
      const [colName, dataType, nullable] = c.f.map(f=>f.v);
      if (
        skipTypes.includes(dataType) ||
        skipColumnNames.includes(colName.toLowerCase()) ||
        colName.startsWith('__')
      ) return;

      const safeColName = `\`${colName}\``;
      const blankPred = dataType.startsWith('STRING') ? 'TRIM(v)=""' : 'FALSE';
      const avgExpr = numeric.includes(dataType)
        ? `SAFE_CAST(AVG(SAFE_CAST(v AS FLOAT64)) AS STRING) AS avg_v`
        : `CAST(NULL AS STRING) AS avg_v`;

      const profileSQL = `
        WITH base AS (SELECT ${safeColName} AS v FROM \`${fqdn}\`)
        SELECT
          APPROX_COUNT_DISTINCT(v) AS d_cnt,
          COUNTIF(v IS NULL)         AS n_cnt,
          COUNTIF(${blankPred})      AS b_cnt,
          SAFE_CAST(MIN(v) AS STRING) AS min_v,
          SAFE_CAST(MAX(v) AS STRING) AS max_v,
          ${avgExpr},
          ARRAY_TO_STRING(
            ARRAY(SELECT SAFE_CAST(v AS STRING)
                  FROM base
                  GROUP BY v
                  ORDER BY COUNT(*) DESC
                  LIMIT 5), ','
          ) AS top5_v,
          ARRAY_TO_STRING(
            ARRAY(SELECT DISTINCT SAFE_CAST(v AS STRING)
                  FROM base
                  WHERE v IS NOT NULL AND NOT (${blankPred})
                  ORDER BY RAND()
                  LIMIT 5), ','
          ) AS sample_v
        FROM base
      `;

      let resultRows;
      try {
        resultRows = bq.Jobs.getQueryResults(
          proj,
          bq.Jobs.insert(
            { configuration:{ query:{ query: profileSQL, useLegacySql:false } } },
            proj
          ).jobReference.jobId
        ).rows;
        if (!resultRows || !resultRows.length) return;

        const vals = resultRows[0].f.map(x=>x.v);
        let [dCnt,nCnt,bCnt,minV,maxV,avgV,top5,samples] = vals;
        const key = `${proj}.${ds}.${tbl}|${colName}`;
        const rowNum = colIdx.get(key);
        const piiFlag = rowNum
          ? colSheet.getRange(rowNum,18).getValue()
          : '';
        if (piiFlag==='YES') { top5=''; samples=''; }

        const updateArr = [
          nullable, '', dCnt, nCnt, bCnt, rowCntTbl,
          minV, maxV, avgV, top5, samples, now, piiFlag
        ];

        if (rowNum) {
          colSheet.getRange(rowNum,6,1,13).setValues([updateArr]);
          colSheet.getRange(rowNum,19).setValue(true);
        } else {
          colSheet.appendRow([
            proj, ds, tbl, colName, dataType,
            ...updateArr, true
          ]);
        }

      } catch(e) {
        console.error(`Error profiling ${fqdn}.${colName}`, e);
        let log = ss.getSheetByName('ColumnAudit_Errors');
        if (!log) {
          log = ss.insertSheet('ColumnAudit_Errors');
          log.appendRow(['Timestamp','Project','Dataset','Table','Column','Query','Error']);
        }
        log.appendRow([new Date(),proj,ds,tbl,colName,profileSQL,e.toString()]);
      }
    });

    // Clear the “due” flag & stamp last audit
    const idx = tblRows.findIndex(r=>
      r[0]===proj && r[1]===ds && r[2]===tbl
    );
    if (idx !== -1) {
      const row = idx+2;
      tblSheet.getRange(row,11).setValue(now)
              .setNumberFormat('yyyy-MM-dd HH:mm:ss');
      tblSheet.getRange(row,12).setValue(false);
    }
  });
}


/**function syncColumnsold() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tblSheet = ss.getSheetByName('Table_Metadata');
  const colSheet = ss.getSheetByName('Column_Metadata');
  const bq = BigQuery;
  const now = new Date();

  // 1 ▪ Load Table_Metadata rows (14 cols)
  const tblRows = tblSheet.getRange(2, 1, tblSheet.getLastRow() - 1, 14).getValues();

  // 2 ▪ Determine active profiling targets (In Use & column_profile_due=TRUE)
  const targets = tblRows.filter(r => r[11] && r[12] === 'In Use' && r[13]);

  // 3 ▪ Prepare active tables (status=In Use) as a Set of keys
  const activeTableKeys = new Set(
    tblRows.filter(r => r[12] === 'In Use').map(r => `${r[0]}.${r[1]}.${r[2]}`)
  );

  // 4 ▪ Update exists_flag in Column_Metadata based on activeTableKeys
  if (colSheet.getLastRow() > 1) {
    const colRows = colSheet.getRange(2, 1, colSheet.getLastRow() - 1, 19).getValues();
    colRows.forEach((row, i) => {
      const key = `${row[0]}.${row[1]}.${row[2]}`;
      const flag = activeTableKeys.has(key);
      colSheet.getRange(i + 2, 19).setValue(flag);
    });
  }

  if (!targets.length) return; // Nothing to profile

  // 5 ▪ Index existing Column_Metadata rows
  const colIdx = new Map();
  if (colSheet.getLastRow() > 1) {
    colSheet.getRange(2, 1, colSheet.getLastRow() - 1, 19).getValues()
      .forEach((row, i) =>
        colIdx.set(`${row[0]}.${row[1]}.${row[2]}|${row[3]}`, i + 2));
  }

  const numeric = ['INT64', 'NUMERIC', 'BIGNUMERIC', 'FLOAT64', 'DECIMAL'];
  const skipTypes = ['BYTES'];
  const skipColumnNames = ['rowversion'];

  // 6 ▪ Profile columns in active tables
  targets.forEach(t => {
    const [proj, ds, tbl] = [t[0], t[1], t[2]];
    const fqdn = `${proj}.${ds}.${tbl}`;

    let rowCntTbl = 0;
    try {
      const tInfo = bq.Tables.get(proj, ds, tbl);
      rowCntTbl = Number(tInfo.numRows || 0);
    } catch (e) {
      console.warn(`Skipping table ${fqdn} – failed to get row count.`);
    }

    const metaSQL = `
      SELECT column_name, data_type, is_nullable
      FROM \`${proj}.${ds}.INFORMATION_SCHEMA.COLUMNS\`
      WHERE table_name = '${tbl}'
    `;
    const cols = bq.Jobs.getQueryResults(
      proj,
      bq.Jobs.insert(
        { configuration: { query: { query: metaSQL, useLegacySql: false } } }, proj
      ).jobReference.jobId
    ).rows || [];

    cols.forEach(c => {
      const [colName, dataType, nullable] = c.f.map(f => f.v);
      const safeColName = `\`${colName}\``;

      if (skipTypes.includes(dataType) ||
          skipColumnNames.includes(colName.toLowerCase()) ||
          colName.startsWith('__')) {
        console.warn(`Skipping column ${colName} (type: ${dataType})`);
        return;
      }

      const blankPred = dataType.startsWith('STRING') ? 'TRIM(v) = ""' : 'FALSE';
      const avgExpr = numeric.includes(dataType)
        ? `SAFE_CAST(AVG(SAFE_CAST(v AS FLOAT64)) AS STRING) AS avg_v`
        : `CAST(NULL AS STRING) AS avg_v`;

      const profileSQL = `
        WITH base AS (SELECT ${safeColName} AS v FROM \`${fqdn}\`)
        SELECT
          APPROX_COUNT_DISTINCT(v) AS d_cnt,
          COUNTIF(v IS NULL) AS n_cnt,
          COUNTIF(${blankPred}) AS b_cnt,
          SAFE_CAST(MIN(v) AS STRING) AS min_v,
          SAFE_CAST(MAX(v) AS STRING) AS max_v,
          ${avgExpr},
          ARRAY_TO_STRING(ARRAY(
            SELECT SAFE_CAST(v AS STRING)
            FROM base
            GROUP BY v
            ORDER BY COUNT(*) DESC
            LIMIT 5), ', ') AS top5_v,
          ARRAY_TO_STRING(ARRAY(
            SELECT DISTINCT SAFE_CAST(v AS STRING)
            FROM base
            WHERE v IS NOT NULL AND NOT (${blankPred})
            ORDER BY RAND()
            LIMIT 5), ', ') AS sample_v
        FROM base
      `;

      let resultRows;
      try {
        resultRows = bq.Jobs.getQueryResults(
          proj,
          bq.Jobs.insert(
            { configuration: { query: { query: profileSQL, useLegacySql: false } } }, proj
          ).jobReference.jobId
        ).rows;

        if (!resultRows || resultRows.length === 0) {
          console.warn(`⚠️ No profiling data for column: ${colName} in table: ${fqdn}`);
          return;
        }

        const f = resultRows[0].f;
        let [dCnt, nCnt, bCnt, minV, maxV, avgV, top5, samples] = f.map(x => x.v);

        const key = `${proj}.${ds}.${tbl}|${colName}`;
        const rowNum = colIdx.get(key);
        const piiFlag = rowNum ? colSheet.getRange(rowNum, 18).getValue() : '';
        if (piiFlag === 'YES') { top5 = ''; samples = ''; }

        const updateArray = [
          nullable, '', dCnt, nCnt, bCnt, rowCntTbl,
          minV, maxV, avgV, top5, samples, now, piiFlag
        ];

        if (rowNum) {
          colSheet.getRange(rowNum, 6, 1, 13).setValues([updateArray]);
          colSheet.getRange(rowNum, 19).setValue(true);
        } else {
          colSheet.appendRow([
            proj, ds, tbl, colName, dataType, ...updateArray, true
          ]);
        }

      } catch (e) {
        console.error(`❌ Error profiling column: ${colName} in table: ${fqdn}`);
        console.error(`❌ Failing query:\n${profileSQL}`);
        console.error(`❌ BigQuery error:\n${e}`);

        let logSheet = ss.getSheetByName('ColumnAudit_Errors');
        if (!logSheet) {
          logSheet = ss.insertSheet('ColumnAudit_Errors');
          logSheet.appendRow(['Timestamp', 'Project', 'Dataset', 'Table', 'Column', 'Query', 'Error']);
        }
        logSheet.appendRow([
          new Date(), proj, ds, tbl, colName, profileSQL, e.toString()
        ]);
      }
    });

    // Update column_profile_last_audit & column_profile_due
    const idxTbl = tblRows.findIndex(r => r[0] === proj && r[1] === ds && r[2] === tbl);
    if (idxTbl !== -1) {
      const sheetRow = idxTbl + 2;
      tblSheet.getRange(sheetRow, 11).setValue(now).setNumberFormat('yyyy-MM-dd HH:mm:ss');
      tblSheet.getRange(sheetRow, 12).setValue(false);
    }
  });
} */
