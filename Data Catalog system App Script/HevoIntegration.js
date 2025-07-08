/**
 * Fetch Hevo Models (table transformation queries) from Hevo API
 * and store them in a sheet "Hevo_Models".
 */
function fetchHevoModels() {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Hevo_Models') ||
                  SpreadsheetApp.getActiveSpreadsheet().insertSheet('Hevo_Models');
    sheet.clear(); // clear old data

    // Prepare headers
    const headers = ['project_id', 'dataset_id', 'table_id', 'table_fqdn', 
                      'hevo_id', 'hevo_subject_name', 'status', 
                      'source_query', 'last_run_ts'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

    // Call Hevo API
    const url = `${HEVO_CRED.api_host}/api/public/v2.0/models`;
    const headersApi = {
      'Authorization': 'Basic ' + Utilities.base64Encode(`${HEVO_CRED.access_key}:${HEVO_CRED.secret_key}`),
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    const options = {
      'method': 'get',
      'headers': headersApi
    };
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();

    if (responseCode === 200) {
      const models = JSON.parse(response.getContentText()).data;

      // Prepare rows
      const rows = models.map(m => {
        const projectId = m.destination.config.project_id || '';
        const datasetId = m.destination.config.dataset_name || '';
        const tableId = m.output_table || '';
        const fqdn = projectId && datasetId && tableId ? `${projectId}.${datasetId}.${tableId}` : '';

        const lastRunTimestamp = m.last_run_ts ? 
          Utilities.formatDate(new Date(Number(m.last_run_ts)), 'GMT', 'yyyy-MM-dd HH:mm:ss') : '';

        return [
          projectId,
          datasetId,
          tableId,
          fqdn,
          m.id || '',
          m.name || '',
          m.status || '',
          m.source_query || '',
          lastRunTimestamp
        ];
      });

      // Write rows
      if (rows.length) {
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      }
    } else {
      console.error('Error Response: ' + response.getContentText());
    }
  } catch (error) {
    console.error('Error in fetchHevoModels():', error);
  }
}


/**
 * Process Hevo Models data and insert only relevant fields (starting at column A).
 */
function processHevoModels(data, sheet) {
  const relevantKeys = [
    "project_id",
    "dataset_id",
    "table_id",
    "table_fqdn",
    "hevo_id",
    "hevo_subject_name",
    "status",
    "source_query",
    "last_run_ts"
  ];

  // Set header row (starting at column A)
  sheet.getRange(1, 1, 1, relevantKeys.length).setValues([relevantKeys]);

  let lastRow = 1;
  data.forEach(function (model) {
    let flattened = getAllKeys(model);

    // Map fields from API response
    flattened["project_id"] = flattened["destination.config.project_id"] || "";
    flattened["dataset_id"] = flattened["destination.config.dataset_name"] || "";
    flattened["table_id"] = flattened["output_table"] || "";
    flattened["table_fqdn"] = `${flattened["project_id"]}.${flattened["dataset_id"]}.${flattened["table_id"]}`;
    flattened["hevo_id"] = flattened["id"];
    flattened["hevo_subject_name"] = flattened["name"]; // rename "name" to "hevo_subject_name"

    // Determine final row data
    const finalRow = relevantKeys.map(key => flattened[key] || "");
    sheet.getRange(lastRow + 1, 1, 1, relevantKeys.length).setValues([finalRow]);
    lastRow++;
  });
}

/**
 * Helper: Flatten nested JSON keys into a flat object.
 */
function getAllKeys(obj, prefix = '') {
  let result = {};
  for (let key in obj) {
    let newKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
      Object.assign(result, getAllKeys(obj[key], newKey));
    } else {
      result[newKey] = obj[key];
    }
  }
  return result;
}

/**
 * Check and delete rows no longer present in API response.
 */
function checkAndDeleteDataInSheet(sheet, apiIdArr) {
  let existingIds = sheet.getRange(2, 5, sheet.getLastRow() - 1, 1).getValues().flat(); // 5th column (hevo_id)
  for (let i = existingIds.length - 1; i >= 0; i--) {
    if (!apiIdArr.includes(existingIds[i])) {
      sheet.deleteRow(i + 2);
    }
  }
}
