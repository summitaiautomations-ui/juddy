# eBay API setup (one-time)

The `ebay-draft` command pushes a fully-populated draft listing into your eBay
seller hub from a folder of disc photos. To wire it up you need eBay developer
credentials (free) and a single OAuth consent click.

## 1. eBay developer account

1. Go to https://developer.ebay.com and sign in with your eBay account.
2. Accept the developer agreement (one-time).
3. **Application Keys** → **Create a Keyset** for **Production**. You'll get
   three values — copy them somewhere safe for the next step:
   - **App ID** (Client ID)
   - **Cert ID** (Client Secret)
   - **Dev ID**

## 2. Set the Redirect URL (RuName)

Still on developer.ebay.com:

1. In your production keyset row, click **User Tokens** →
   **Get a Token from eBay via Your Application**.
2. Under "Add Eligible Redirect URI Name", click **Add eBay Redirect URL**.
3. Auth Accepted URL: `http://localhost:8765/callback`
4. Auth Declined URL: `http://localhost:8765/callback`
5. Privacy Policy URL: any URL you control (your linktr.ee works).
6. Save. Note the **RuName** eBay generates (looks like
   `Justin_Neal-JustinNe-Discs-abcdef`).

## 3. Add credentials to `~/juddy/.env`

```
EBAY_APP_ID=<your App ID>
EBAY_CERT_ID=<your Cert ID>
EBAY_DEV_ID=<your Dev ID>
EBAY_RU_NAME=<the RuName from step 2>
```

## 4. Set up Business Policies on your seller account

eBay's Sell API requires you to use Business Policies for shipping / returns /
payments. If you don't already have them:

1. Seller Hub → **Account settings** → **Business Policies**.
2. Create at least one of each:
   - **Shipping (Fulfillment)** policy — your default ship method/cost
   - **Payment** policy — usually eBay-managed payments, no config needed
   - **Return** policy — your return window + who pays return shipping
3. Save them. The `ebay-setup` command picks up the first of each
   automatically.

## 5. Run the one-time setup

```bash
cd ~/juddy
discs/.venv/bin/python -m discs ebay-setup
```

This will:

1. Open a browser to eBay's OAuth consent page → sign in → approve.
2. Capture the auth code on `http://localhost:8765/callback`.
3. Exchange it for a refresh token (saved to `discs/.ebay_state.json`,
   gitignored).
4. Fetch your Business Policy IDs and save them.
5. Prompt for your shipping ZIP and create a default inventory location.

After that, sanity-check:

```bash
discs/.venv/bin/python -m discs ebay-test
```

Should print your policy names + IDs and the active location.

## 6. Create your first draft listing

```bash
mkdir -p ~/Desktop/destroyer-172-yellow
# put 3-4 photos in there: stamp.jpg, back.jpg, profile.jpg, weight.jpg
# optionally put price.txt with just the dollar amount: 25
discs/.venv/bin/python -m discs ebay-draft ~/Desktop/destroyer-172-yellow
```

The command will:

1. Send all photos to Claude for identification + listing copy
2. Upload the photos to eBay's picture service (no third-party host)
3. Create an inventory item with title, description, condition, aspects
4. Create an UNPUBLISHED offer at your price → draft sits in Seller Hub
5. Print the Seller Hub drafts URL — open it, review, click **Publish**

## Troubleshooting

- **"No fulfillment policies"** — create them in Seller Hub before running
  `ebay-setup`.
- **Token expired / 401** — the client auto-refreshes, but if the refresh
  token itself dies (~18 months) just re-run `ebay-setup`.
- **Wrong category** — eBay leaf category IDs change occasionally. Edit
  `discs/ebay/categories.py` if a listing lands in the wrong subcategory.
- **`discs/.ebay_state.json` is gitignored** — never commit it, it has
  long-lived OAuth tokens.
