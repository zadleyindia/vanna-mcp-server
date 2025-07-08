/********************************************************************
 *  PUSH CATALOG SHEETS -> BIGQUERY  (auto-create dataset & tables)
 *  Project : bigquerylascoot     |  Dataset : metadata_data_dictionary (US)
 ********************************************************************/

/* ----------  SCHEMA DEFINITIONS  ---------- */

/* 1 ▪ Datasets (12 cols) */
const datasetsSchema = [
  {name:'project_id',           type:'STRING'},
  {name:'dataset_id',           type:'STRING'},
  {name:'dataset_fqdn',         type:'STRING'},
  {name:'business_domain',      type:'STRING'},
  {name:'dataset_type',         type:'STRING'},
  {name:'owner_email',          type:'STRING'},
  {name:'refresh_cadence',      type:'STRING'},
  {name:'source_system',        type:'STRING'},
  {name:'description',          type:'STRING'},
  {name:'row_count_last_audit', type:'INT64'},
  {name:'last_updated_ts',      type:'TIMESTAMP'},
  {name:'status',               type:'STRING'}
];

/* 2 ▪ Table_Metadata (14 cols) */
const tableSchema = [
  {name:'project_id',                type:'STRING'},
  {name:'dataset_id',                type:'STRING'},
  {name:'table_id',                  type:'STRING'},
  {name:'table_fqdn',                type:'STRING'},
  {name:'object_type',               type:'STRING'},
  {name:'business_domain',           type:'STRING'},
  {name:'grain_description',         type:'STRING'},
  {name:'row_count_last_audit',      type:'INT64'},
  {name:'column_count',              type:'INT64'},
  {name:'last_updated_ts',           type:'TIMESTAMP'},
  {name:'column_profile_last_audit', type:'TIMESTAMP'},
  {name:'column_profile_due',        type:'BOOL'},
  {name:'status',                    type:'STRING'},
  {name:'exists_flag',               type:'BOOL'}
];

/* 3 ▪ Column_Metadata (19 cols incl. row_count) */
const columnSchema = [
  {name:'project_id',        type:'STRING'},
  {name:'dataset_id',        type:'STRING'},
  {name:'table_id',          type:'STRING'},
  {name:'column_name',       type:'STRING'},
  {name:'data_type',         type:'STRING'},
  {name:'is_nullable',       type:'STRING'},
  {name:'description',       type:'STRING'},
  {name:'distinct_count',    type:'INT64'},
  {name:'null_count',        type:'INT64'},
  {name:'blank_count',       type:'INT64'},
  {name:'row_count',         type:'INT64'},
  {name:'min_value',         type:'STRING'},
  {name:'max_value',         type:'STRING'},
  {name:'average_value',     type:'STRING'},
  {name:'top_5_values',      type:'STRING'},
  {name:'sample_values',     type:'STRING'},
  {name:'profile_timestamp', type:'TIMESTAMP'},
  {name:'pii_flag',          type:'STRING'},
  {name:'exists_flag',       type:'BOOL'}
];

/* 4 ▪ View_Definitions (5 cols including view_type) */
const viewSchema = [
  {name:'project_id',  type:'STRING'},
  {name:'dataset_id',  type:'STRING'},
  {name:'view_name',   type:'STRING'},
  {name:'sql_query',   type:'STRING'},
  {name:'view_type',   type:'STRING'}  // ✅ new column
];


/* 5 ▪ Hevo_Models (9 cols) */
const hevoSchema = [
  {name:'project_id',          type:'STRING'},
  {name:'dataset_id',          type:'STRING'},
  {name:'table_id',            type:'STRING'},
  {name:'table_fqdn',          type:'STRING'},
  {name:'hevo_id',             type:'STRING'},
  {name:'hevo_subject_name',   type:'STRING'},
  {name:'status',              type:'STRING'},
  {name:'source_query',        type:'STRING'},
  {name:'last_run_ts',         type:'TIMESTAMP'}
];

/* ----------  HELPERS  ---------- */
function ensureDataset() {
  try {
    BigQuery.Datasets.get(PROJECT, DATASET);
  } catch (e) {
    if (e.toString().includes('Not found')) {
      BigQuery.Datasets.insert(
        { datasetReference:{ projectId: PROJECT, datasetId: DATASET }, location:'US' },
        PROJECT
      );
    } else {
      throw e;
    }
  }
}

function ensureTable(tableId, schemaFields) {
  try {
    BigQuery.Tables.get(PROJECT, DATASET, tableId);
  } catch (e) {
    if (e.toString().includes('Not found')) {
      BigQuery.Tables.insert(
        {
          tableReference:{ projectId:PROJECT, datasetId:DATASET, tableId },
          schema:{ fields: schemaFields }
        },
        PROJECT,
        DATASET
      );
    } else {
      throw e;
    }
  }
}

function sheetToRows(values) {
  const headers = values[0];
  const fix = (val) => {
    if (val === '' || val === null) return null;
    if (val === 'TRUE')  return true;
    if (val === 'FALSE') return false;
    if (val instanceof Date) {
      return Utilities.formatDate(val, 'UTC', 'yyyy-MM-dd HH:mm:ss');
    }
    return val;
  };

  return values.slice(1)
               .filter(r => r.some(v => v !== ''))
               .map(row => ({
                 json: headers.reduce((o, h, i) => {
                   o[h] = fix(row[i]);
                   return o;
                 }, {})
               }));
}

function uploadSheet(sheetName, tableId, schema) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(sheetName);
  if (!sh) throw new Error(`Sheet '${sheetName}' not found`);
  const data = sh.getDataRange().getValues();
  if (data.length <= 1) return;

  ensureTable(tableId, schema);

  BigQuery.Jobs.query({
    query:`TRUNCATE TABLE \`${PROJECT}.${DATASET}.${tableId}\``,
    useLegacySql:false,
    location:'US'
  }, PROJECT);

  const rows = sheetToRows(data);
  while (rows.length) {
    BigQuery.Tabledata.insertAll(
      { rows: rows.splice(0,500), skipInvalidRows:true, ignoreUnknownValues:true },
      PROJECT, DATASET, tableId
    );
  }
}

/* ----------  MAIN ENTRY ---------- */
function pushCatalogToBQ() {
  ensureDataset();
  uploadSheet('Datasets',         'Datasets',         datasetsSchema);
  uploadSheet('Table_Metadata',   'Table_Metadata',   tableSchema);
  uploadSheet('Column_Metadata',  'Column_Metadata',  columnSchema);
  uploadSheet('View_Definitions', 'View_Definitions', viewSchema);
  uploadSheet('Hevo_Models',      'Hevo_Models',      hevoSchema);   // 🔥 new!
}
