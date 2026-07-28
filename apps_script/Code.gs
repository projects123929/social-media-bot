/**
 * Google Apps Script Web App — bridges the Cartoon Short Pipeline dashboard
 * sheet and Gmail to GitHub Actions, with NO Google Cloud Console setup.
 *
 * How to install: see docs/GITHUB_NATIVE_SHEETS_SETUP.md. Short version —
 * paste this whole file into Extensions > Apps Script in the dashboard
 * spreadsheet, set SHARED_SECRET below, then Deploy > New deployment >
 * Web app (Execute as: Me, Who has access: Anyone).
 *
 * This script runs as whoever deployed it (should be ai@ms2.co.in) and
 * uses that account's own Sheets + Gmail access automatically — that's
 * why no separate credentials are needed.
 */

// Change this to any random string, then use the SAME value as the
// GAS_SHARED_SECRET GitHub secret. Prevents randoms from calling your
// Web App URL if they ever guess/find it.
var SHARED_SECRET = "1ERSAZZMyk-NV9x2agGspbXIdu3-LnsjRfpTSoZizAM";

var SHEET_NAME = "Sheet1";
// Order here MUST exactly match the physical column order in the sheet
// (A, B, C, ...) - this maps by position, not by searching for header text.
var COLUMNS = ["Video Title", "Video Length", "Aspect Ratio", "Status", "Progress", "Approval Status", "Upload Status", "YouTube Status", "Last Updated", "Video URL"];

function doPost(e) {
  var body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return _json({ error: "Invalid JSON body" }, 400);
  }
  return _handle(body);
}

// GET-based entry point, preferred by the Python client: Apps Script Web
// Apps always respond via a 302 to a second "echo" URL, and POST requests
// to that mechanism have proven unreliable across HTTP clients (lost
// body, 411s, empty responses). GET has no body to lose, sidestepping the
// whole problem. `values` (an object) is passed JSON-encoded in the
// `values` query param.
function doGet(e) {
  var body = {
    action: e.parameter.action,
    secret: e.parameter.secret,
    row: e.parameter.row ? Number(e.parameter.row) : undefined,
    subject: e.parameter.subject,
    html_body: e.parameter.html_body,
    to: e.parameter.to,
    subject_contains: e.parameter.subject_contains,
  };
  if (e.parameter.values) {
    try {
      body.values = JSON.parse(e.parameter.values);
    } catch (err) {
      return _json({ error: "Invalid JSON in values param" }, 400);
    }
  }
  return _handle(body);
}

function _handle(body) {
  if (body.secret !== SHARED_SECRET) {
    return _json({ error: "Bad secret" }, 403);
  }

  try {
    switch (body.action) {
      case "get_rows":
        return _json({ rows: _getRows() });
      case "update_row":
        _updateRow(body.row, body.values);
        return _json({ ok: true, row: body.row, updated: body.values });
      case "send_email":
        _sendEmail(body.subject, body.html_body, body.to);
        return _json({ ok: true });
      case "check_reply":
        return _json({ result: _checkReply(body.subject_contains) });
      default:
        return _json({ error: "Unknown action: " + body.action }, 400);
    }
  } catch (err) {
    return _json({ error: String(err) }, 500);
  }
}

function _sheet() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
}

function _getRows() {
  var sheet = _sheet();
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];
  var values = sheet.getRange(2, 1, lastRow - 1, COLUMNS.length).getValues();
  var rows = [];
  for (var i = 0; i < values.length; i++) {
    var entry = { row_number: i + 2 };
    for (var j = 0; j < COLUMNS.length; j++) {
      entry[COLUMNS[j]] = values[i][j] === null ? "" : String(values[i][j]);
    }
    rows.push(entry);
  }
  return rows;
}

function _updateRow(rowNumber, values) {
  var sheet = _sheet();
  for (var colName in values) {
    var colIndex = COLUMNS.indexOf(colName);
    if (colIndex === -1) throw new Error("Unknown column: " + colName);
    sheet.getRange(rowNumber, colIndex + 1).setValue(values[colName]);
  }
  SpreadsheetApp.flush();
}

function _sendEmail(subject, htmlBody, to) {
  GmailApp.sendEmail(to, subject, "", { htmlBody: htmlBody });
}

function _checkReply(subjectContains) {
  var threads = GmailApp.search('subject:"' + subjectContains + '" newer_than:7d', 0, 5);
  for (var t = 0; t < threads.length; t++) {
    var messages = threads[t].getMessages();
    if (messages.length < 2) continue; // only the original sent message, no reply yet
    var reply = messages[messages.length - 1];
    var text = reply.getPlainBody().trim().toLowerCase();
    if (text.indexOf("approve") === 0) return "approve";
    if (text.indexOf("reject") === 0) return "reject";
  }
  return null;
}

function _json(obj, statusCode) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
