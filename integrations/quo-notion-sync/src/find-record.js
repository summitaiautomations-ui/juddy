// Quick manual test: node src/find-record.js "+1 612-352-7343"
// Verifies your Notion token + phone matching before wiring up Quo.
import { findRecordByPhone } from './notion.js';

const phone = process.argv[2];
if (!phone) {
  console.error('Usage: node src/find-record.js "<phone number>"');
  process.exit(1);
}

const record = await findRecordByPhone(phone);
if (record) {
  console.log(`Matched ${record.ds.key} record: ${record.pageId} (Notion phone: ${record.phone})`);
} else {
  console.log(`No record matched ${phone}`);
}
