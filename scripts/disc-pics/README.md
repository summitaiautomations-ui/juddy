# disc-pics: Photo Booth → disc inventory

Photograph your discs with the Mac's built-in **Photo Booth** app, then let
Claude identify each one and build a searchable inventory.

```
Photo Booth --import.sh--> inbox/ --catalog.sh--> disc-pics-data/ --sync.sh--> GitHub --> Google Sheet
```

The inbox lives under `~/Pictures/disc-pics/` (override with `DISC_PICS_DIR`);
everything cataloged lives in the repo so it can be shared:

| Path                          | What it is                                          |
|-------------------------------|-----------------------------------------------------|
| `~/Pictures/disc-pics/inbox/` | Imported photos waiting to be identified            |
| `disc-pics-data/photos/`      | Cataloged photos, renamed like `007-champion-destroyer.jpg` |
| `disc-pics-data/inventory.csv`| One row per disc: mold, brand, plastic, color, weight, condition, price, notes |
| `disc-pics-data/sheet.csv`    | Same rows plus a public photo URL -- the Google Sheet feed |

## Fully automatic mode

```bash
./install.sh
```

Installs a LaunchAgent (`com.juddy.disc-pics`) that watches the Photo Booth
library and runs import + catalog + sync by itself every time you snap a
photo. Snap a disc, and ~30 seconds later it's identified, priced, filed,
pushed to GitHub, and on its way into the shared Google Sheet.
Log: `~/Library/Logs/juddy/disc-pics.log`.

## Shared Google Sheet (one-time setup)

The Mac mini pushes `disc-pics-data/` to GitHub; a Google Sheet reads it
live over raw URLs. Set it up once:

1. Create a blank sheet at [sheets.new](https://sheets.new).
2. In **B1**:

   ```
   =IMPORTDATA("https://raw.githubusercontent.com/<owner>/<repo>/<branch>/disc-pics-data/sheet.csv")
   ```

   (`<branch>` = whatever branch the Mac mini is checked out on.)
3. In **A1** type `Pic`, and in **A2**:

   ```
   =ARRAYFORMULA(IF(LEN(B2:B), IMAGE(B2:B), ""))
   ```
4. Format > Rows > taller rows so the pictures show, then **Share** with
   your friend (viewer).

Google refreshes `IMPORTDATA` roughly hourly. New discs appear on their own.

> **Privacy note:** this only works because the repo is public -- the photos,
> prices, and notes in `disc-pics-data/` are visible to anyone with the link.
> Don't put anything personal in the notes.

## Pricing

Claude suggests an asking price per disc, anchored to the local-shop
economics: the shop pays **$3** flat, an average used disc lists at **$9**.
Beat-in base plastic runs $5-7, near-new premium plastic $10-14, hot molds
and limited/tour stamps $15+. Anything it would price under ~$5 is usually
not worth the hassle -- just take the shop's $3.

## One-time Photo Booth setup

1. Open Photo Booth. In the menu bar, enable **Edit → Auto Flip New Items**.
   Photo Booth mirrors photos by default, which makes disc stamps read
   backwards. (Forgot? Run `FLIP=1 ./import.sh` to un-mirror on import.)
2. Turn the screen-flash on (the camera button flashes the display white) --
   it doubles as a fill light.

## Taking good disc pics

- Plain, contrasting background: a sheet of white or black poster board.
- Stamp side up, disc flat, fill most of the frame.
- If the weight is written on the disc or rim, angle it into the shot once --
  Claude will pick it up for the inventory.
- Beat-in discs: take a second shot of the wear/dome if you plan to sell or
  trade; extra shots of the same disc just become extra rows you can merge.

## Usage

```bash
cd scripts/disc-pics

# 1. Snap your discs in Photo Booth, then:
./import.sh          # pull new photos into the inbox
FLIP=1 ./import.sh   # same, but un-mirror (if Auto Flip was off)

# 2. Identify everything in the inbox:
./catalog.sh
```

`catalog.sh` sends each photo to the `claude` CLI, appends a row to
`inventory.csv`, and moves the photo into `library/` renamed with its ID and
mold. Photos it can't confidently parse stay in the inbox so you can retry or
fill the row in by hand.

Both scripts are idempotent: import skips anything it has seen before, and
catalog only touches what's in the inbox.

## Knobs

| Variable          | Default                                    | Purpose                     |
|-------------------|--------------------------------------------|-----------------------------|
| `DISC_PICS_DIR`   | `~/Pictures/disc-pics`                     | Where everything is stored  |
| `PHOTO_BOOTH_DIR` | `~/Pictures/Photo Booth Library/Pictures`  | Where Photo Booth saves     |
| `FLIP=1`          | off                                        | Un-mirror photos on import  |
| `CLAUDE_BIN`      | `claude` on PATH                           | Claude CLI location         |
