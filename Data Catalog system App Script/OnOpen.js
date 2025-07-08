/**
 * OnOpen.gs
 *
 * When the spreadsheet opens, add a “📒 Catalog” menu with several items.
 * – Calls local functions (no external library).
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('📒 Catalog')
    .addItem('Sync Dataset Metrics', 'syncDatasets')         // Calls local syncDatasets()
    .addItem('Sync Table Metrics', 'syncTables')             // Calls local syncTables()
    .addItem('Sync Column Metrics', 'syncColumns')           // Calls local syncColumns()
    .addItem('Fetch Hevo Models', 'fetchHevoModels')         // 🔥 NEW: fetch Hevo Models
    .addItem('Fetch View Queries', 'syncViewQueries')        // ✅ NEW: syncViewQueries()
    .addSeparator()
    .addItem('↪ Push to BigQuery', 'pushCatalogToBQ')        // Calls local pushCatalogToBQ()
    .addSeparator()
    .addItem('Export Catalog as JSON', 'exportCatalogJSONFromBQ') // Calls exportCatalogJSONFromBQ()
    .addToUi();
}
