import 'dotenv/config';

function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

export const config = {
  notionToken: required('NOTION_TOKEN'),
  // The base64 "signing key" shown in Quo's webhook settings.
  quoSigningKey: process.env.QUO_SIGNING_KEY || '',
  port: Number(process.env.PORT || 8080),
  defaultCountryCode: process.env.DEFAULT_COUNTRY_CODE || '1',
  phoneCacheTtlSeconds: Number(process.env.PHONE_CACHE_TTL_SECONDS || 120),

  // Each pipeline we sync into. `phoneProp` is the phone field; `touchpointProp`
  // is set to "Text" when present; `channelProp` (multi-select) gets "Quo" added.
  dataSources: [
    {
      key: 'recruiting',
      id: process.env.NOTION_RECRUITING_DS || 'db7b25ed-d721-4a52-974b-58b3379f5309',
      titleProp: 'Candidate Name',
      phoneProp: 'Phone',
      lastContactProp: 'Last Contact',
      touchpointProp: 'Last Touchpoint Type', // select; will set to "Text"
      channelProp: null,
    },
    {
      key: 'mortgage',
      id: process.env.NOTION_MORTGAGE_DS || '4a3cbfe3-76a4-486f-8254-0b0b9c9d4115',
      titleProp: 'Lead Name',
      phoneProp: 'Phone',
      lastContactProp: 'Last Contact',
      touchpointProp: null,
      channelProp: 'Communication Channel', // multi-select; will add "Quo"
    },
  ],
};
