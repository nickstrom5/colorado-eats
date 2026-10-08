# App Review: answers prepared before the first submission

Wisconsin Eats got Guideline 2.1 "Information Needed" on 2026-10-05 (a new developer account has a limited review history): Apple
asked for a screen recording from a physical device, starting at launch, and answers to six questions. Colorado Eats should expect the
same, so the reply below goes into **App Review Information → Notes** from the first submission, and the recording is made before
submitting. If Apple asks anyway, paste the same reply into App Review → the submission → **Reply to App Review** and attach the recording.

## Screen recording (Nick, on his iPhone, latest iOS)

The app must be on the phone first, through TestFlight: an internal group with Nick in it. The tester email must be the Apple ID signed
in under Settings › your name › Media & Purchases on the phone; when it isn't, TestFlight shows "not available". Check that first.
Record with Control Center → Screen Recording, 60–120 seconds, no sound needed:

1. Start on the Home Screen and tap **CO Eats**. The recording must begin with the launch.
2. Home: scroll the guide cards a little.
3. Tap **Green Chile**, then tap any place.
4. On the place: tap **Ratings, hours & photos**. Apple's place card opens. Close it.
5. Tap the **heart** (Save), then go back.
6. Back on Home, tap the search box and type `pueblo slopper`. Open a result.
7. Tap the **Map** tab, then tap **Brewpubs**, then a pin and its name.
8. Tap the **Saved** tab, where the saved place shows. Then tap **About** and scroll to the sources.

## Reply text (under 4,000 characters; numbers from playbook/site-numbers.json)

```
Thank you. Here is the information requested.

1. Screen recording from an iPhone on the latest iOS: attached, from launch. There is no account, login, user-generated or paid content.

2. Purpose and audience: Colorado Eats is a free guide to restaurants in Colorado. Its focus is the state's food: 47 green chile spots, 46 ski-town restaurants, 39 game and steak places and the state's oldest restaurants, each checked by hand in fall 2026 against a 2025 or 2026 source (the restaurant's own website or menu, or local news); 234 brewpubs matched to the state's Brew Pub and Distillery Pub licenses; and the MICHELIN Guide Colorado 2026 and James Beard honorees, as facts. It also lists 15,716 restaurants, cafés, bars and bakeries statewide. It is for Colorado residents and visitors deciding where to eat. No ads, account or tracking.

3. How to use it (no login, no setup, no sample files needed):
- Home → any guide (Green Chile, Brewpubs, Ski Town Dining, Game & Steakhouses, MICHELIN & James Beard, Oldest Places, Inspections, Near Me) → tap a place.
- On a place, tap "Ratings, hours & photos" to open Apple Maps' own place card through MapKit. Directions, Call and Website are below it.
- Search by name, town, street or dish ("pueblo slopper", "elk aspen").
- The Map tab shows the Green Chile, Brewpubs, Ski Towns and Honors guides as pins, plus nearby restaurants once zoomed in to a town. "My location" and the Nearest sort use location only if allowed, on the device.
- The heart saves a place on the device, under the Saved tab. The About tab lists the data sources, licenses and the independence statement.
- On iPad, a sidebar replaces the tabs; a place opens in the right-hand column.
- Outside Colorado (as App Review usually is), the map says so and stays on Colorado.
- "CO Eats" is the Home Screen name.

4. External services and data:
- Apple MapKit: maps, local search to find a place's Apple Maps listing, and Apple's place card for live hours, photos and ratings.
- Core Location: optional, on-device only, for distance sorting.
- Core Spotlight: on-device indexing so places appear in iPhone search.
- No backend, accounts, analytics, advertising, payments or AI services. The restaurant data is bundled in the app.
- Bundled data: Overture Maps open data (CDLA Permissive 2.0 and Apache 2.0; license texts in the app); Colorado liquor licenses and Boulder County inspections (data.colorado.gov, public domain); Denver business licenses (open data); MICHELIN and James Beard honors (facts only); and our own research of restaurants' websites, menus and local news.
- Privacy policy and support: a static site on GitHub Pages, https://nickstrom5.github.io/colorado-eats/

5. Regional differences: none. The content covers Colorado; the app works the same everywhere in the United States.

6. Regulated or protected material: the app is not in a regulated industry and includes no protected third-party material. The data is open-licensed or public record, credited on the About tab. Ratings, hours and photos are shown only inside Apple's own place card through MapKit, under Apple's terms; the app stores no ratings or reviews. Boulder County inspection results are shown exactly as the county recorded them (Pass, Re-Inspection Required or Closure), with no grade of our own. Honors are stated as facts, with trademark notices. Website links were checked before release (each must be the restaurant's own page), and strip clubs and other adult venues are excluded by name, address and category. The app is independent and not affiliated with any restaurant, agency, the MICHELIN Guide or the James Beard Foundation.

7. A distinct app: Colorado Eats is built only for Colorado, from Colorado records (state liquor licenses, Denver business licenses, Boulder County inspections) and Colorado-only research (green chile, ski towns, the oldest places, MICHELIN Guide Colorado). Its content isn't shared with any other app.

Support: work-with-nick@gmail.com
```

When the site moves to colorado.eatsranked.com, change the GitHub Pages line in point 4 to the new address. Keep the numbers in points 2
and 3 in step with `playbook/site-numbers.json`, and the reply under 4,000 characters (count it with Python).
