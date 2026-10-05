# Adding Colorado to the eatsranked.com hub (not done: needs Nick's OK, and it's another repo)

The hub lives in `../eatsranked/` (repo nickstrom5/eatsranked). This session only worked in `co-eats/`, so the change is prepared here:
1. Append `eatsranked-entry.json` to `"states"` in `eatsranked/tools/site-data.json` (after WI).
2. Copy `colorado.png` to `eatsranked/docs/icons/colorado.png` (check the size the other icons use).
3. Run `eatsranked/tools/build.py`, check, then commit and push with the no-reply email (Nick's yes first).
When colorado.eatsranked.com resolves, change the three github.io URLs to https://colorado.eatsranked.com/.
