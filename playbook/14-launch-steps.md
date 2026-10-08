# Launch steps (each one needs Nick's explicit yes; none has been done)

## 1. Public website repo + GitHub Pages
Only `docs/`, the app source, scripts and playbook go public; `.gitignore` keeps `data/` (official raw files, research, Google 2021
snapshot), `site/` (the Google-derived leaderboard), build output and the generated Xcode project out. Check with `git status` before the
first commit.
```bash
cd co-eats   # from the claudecode folder
git init -b main
git config user.name "Nick Soderstrom" && git config user.email "329204362+nickstrom5@users.noreply.github.com"
git add -A && git status --short | head -50          # confirm: no data/, site/, .venv/, DerivedData/
git commit -m "Colorado Eats: app, website and pipeline"
gh repo create nickstrom5/colorado-eats --public --source . --push
gh api -X POST repos/nickstrom5/colorado-eats/pages -f "source[branch]=main" -f "source[path]=/docs"
```
Then check that https://nickstrom5.github.io/colorado-eats/, `/privacy.html`, `/terms.html` and `/explore/` return 200.

## 2. colorado.eatsranked.com (Nick, in Cloudflare)
Add `CNAME colorado → nickstrom5.github.io`, **DNS only** (grey cloud). When `dig +short colorado.eatsranked.com CNAME` shows it:
```bash
CO_DOMAIN=colorado.eatsranked.com .venv/bin/python scripts/make-site.py && .venv/bin/python scripts/qa-site.py
git commit -am "Serve from colorado.eatsranked.com" && git push
gh api -X PUT repos/nickstrom5/colorado-eats/pages -f cname=colorado.eatsranked.com
# once the certificate is issued (minutes):
gh api -X PUT repos/nickstrom5/colorado-eats/pages -F https_enforced=true
gh repo edit nickstrom5/colorado-eats --homepage https://colorado.eatsranked.com/
```
The app's links (`ColoradoEats/App/Links.swift`) stay github.io for build 1 (GitHub forwards them); switch them in the next update.

## 3. eatsranked.com hub
`playbook/hub/`: the Colorado entry and icon for `../eatsranked/`, with the steps.

## 4. App Store Connect (Nick creates the record in the web UI; the API can't)
- Register the App ID `com.coloradoeats.ios` (Certificates, Identifiers & Profiles), or let Xcode's automatic signing do it on the
  first signed archive.
- New app: name "Colorado Eats: Restaurants", bundle `com.coloradoeats.ios`, SKU `coloradoeats-ios`, primary language English (U.S.).
- Fill it in from `06-app-store-listing.md`; privacy policy URL on the App Privacy page; "Data Not Collected"; untick "Sign-in required";
  reviewer phone number; price $0.00; availability United States; age rating answers in the listing file (13+).
- The version number must be 1.0.0 to match the build.
- Paste `13-app-review-reply.md`'s reply into App Review Information → Notes; record the screen recording before submitting.

## 5. Archive and upload (public Xcode only)
```bash
cd co-eats   # from the claudecode folder && xcodegen generate
DEVELOPER_DIR="/Applications/Xcode 1.app/Contents/Developer" xcodebuild archive -project ColoradoEats.xcodeproj -scheme ColoradoEats \
  -destination 'generic/platform=iOS' -derivedDataPath ./DerivedData-xc27.0 -archivePath build/ColoradoEats.xcarchive -allowProvisioningUpdates
/usr/libexec/PlistBuddy -c "Print :DTXcodeBuild" build/ColoradoEats.xcarchive/Products/Applications/ColoradoEats.app/Info.plist   # 27A266a, not 27A9xxx
DEVELOPER_DIR="/Applications/Xcode 1.app/Contents/Developer" xcodebuild -exportArchive -archivePath build/ColoradoEats.xcarchive \
  -exportOptionsPlist scripts/ExportOptions-AppStore.plist -exportPath build/export -allowProvisioningUpdates
```
(or `../scripts/testflight.sh`, which pins the public Xcode). Bump `CURRENT_PROJECT_VERSION` in `project.yml` for every upload.
An unsigned check archive with Xcode 27.0 succeeded on 2026-10-05 (DTXcodeBuild 27A266a, 1.0.0 (1)).

## 6. Before submitting (never submit without Nick's yes)
- Re-run `pipeline/check_websites.py`, rebuild with `CO_APP=1`, copy `places.json`, rebuild.
- Unit tests + UI smoke test on "CO Eats 6.9" and "CO Eats iPad 13".
- Screenshots: `docs/screenshots/` (iPhone 1320×2868) and `docs/screenshots/ipad-*` (2064×2752), uploaded one at a time in the order in
  `06-app-store-listing.md`. No Re-Inspection Required or Closure place in any image.
