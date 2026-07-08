/**
 * Disc inventory auto-refresh for Google Sheets.
 *
 * Pulls disc-pics-data/sheet.csv straight from GitHub and rewrites the sheet,
 * building the Pic column from each photo URL. Unlike IMPORTDATA, UrlFetchApp
 * is NOT cached -- so this always shows the latest discs with no formula
 * editing and no cache-busting.
 *
 * ONE-TIME SETUP (in the Google Sheet):
 *   1. Extensions > Apps Script
 *   2. Delete anything there, paste this whole file, click Save (disk icon)
 *   3. In the function dropdown pick "setup", click Run
 *   4. Approve the permission prompt (click Advanced > Go to project > Allow
 *      on the "unverified" screen -- it's your own script)
 *   That's it. The sheet now refreshes every 5 minutes on its own, and a
 *   "Discs" menu appears with a Refresh-now button.
 */

var CSV_URL = "https://raw.githubusercontent.com/summitaiautomations-ui/juddy/claude/photobooth-disc-pics-vueawx/disc-pics-data/sheet.csv";
var ROW_HEIGHT = 100;   // tall enough to see the disc photos
var PIC_COL_WIDTH = 120;

function refreshDiscs() {
  var resp = UrlFetchApp.fetch(CSV_URL + "?t=" + new Date().getTime(),
                               { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) {
    throw new Error("GitHub fetch failed: HTTP " + resp.getResponseCode());
  }
  var data = Utilities.parseCsv(resp.getContentText());
  if (!data.length) return;

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  sheet.clearContents();

  // Prepend a "Pic" column that renders each row's photo_url (column 1).
  var out = [["Pic"].concat(data[0])];
  for (var i = 1; i < data.length; i++) {
    var url = data[i][0];
    var pic = url ? '=IMAGE("' + url + '", 1)' : "";  // mode 1 = fit to cell, keep aspect ratio
    out.push([pic].concat(data[i]));
  }

  sheet.getRange(1, 1, out.length, out[0].length).setValues(out);
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, PIC_COL_WIDTH);
  if (out.length > 1) sheet.setRowHeights(2, out.length - 1, ROW_HEIGHT);
}

// Runs automatically whenever the sheet is opened: adds the menu.
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Discs")
    .addItem("Refresh now", "refreshDiscs")
    .addToUi();
}

// Run this ONCE by hand to authorize, install the 5-minute auto-refresh, and
// do a first pull.
function setup() {
  var existing = ScriptApp.getProjectTriggers();
  for (var i = 0; i < existing.length; i++) {
    if (existing[i].getHandlerFunction() === "refreshDiscs") {
      ScriptApp.deleteTrigger(existing[i]);
    }
  }
  ScriptApp.newTrigger("refreshDiscs").timeBased().everyMinutes(5).create();
  refreshDiscs();
}
