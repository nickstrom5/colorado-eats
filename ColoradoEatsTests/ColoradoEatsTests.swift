import XCTest
import CoreLocation
@testable import ColoradoEats

@MainActor
final class ColoradoEatsTests: XCTestCase {

    /// A tiny data file with the same shape as Resources/places.json.
    private func sampleModel() async throws -> AppModel {
        let json = """
        {"v":1,"generated":"2026-10-05","inspections_through":"2026-07-21","inspections_published":"2026-08-06","liquor_updated":"2026-09-24",
         "cities":["Denver","Pueblo","Boulder","Cañon City","Aspen","Colorado Springs"],"cuisines":["Bar & Pub","Mexican","Steakhouse","Burgers","American & Other"],
         "brands":["Good Times"],"counties":["Denver","Pueblo County","Boulder County","Fremont County","Pitkin County","El Paso County"],
         "srcs":["official","meta","AllThePlaces","DAC","research"],"count":9,"count_restaurants":8,
         "calibration":{"Denver":{"listings":5503,"official_records":6996,"groups":{"meta_high":{"n":1885,"official":0.759},"meta_mid":{"n":342,"official":0.316}}},
                        "Boulder County":{"listings":1952,"official_records":2150,"groups":{"meta_high":{"n":684,"official":0.713},"meta_mid":{"n":144,"official":0.396}}}},
         "places":[
          {"id":"a","n":"Buckhorn Exchange","c":0,"co":0,"cu":2,"t":2,"s":1,"hc":1,"a":"1000 Osage St","z":"80204","la":39.7322,"lo":-105.0034,"j":3,"g":20,"h":16,"ip":54,"f":1893,
           "dish":"bison; elk; Rocky Mountain oysters","liq":"Hotel & Restaurant","lic":[{"src":"Colorado liquor license","id":"03-00001","type":"Hotel & Restaurant","exp":"2027-01-01"}]},
          {"id":"b","n":"Gray's Coors Tavern","c":1,"co":1,"cu":0,"t":2,"s":1,"hc":1,"a":"515 W 4th St","la":38.2711,"lo":-104.6141,"j":3,"g":1,"dish":"slopper; green chile"},
          {"id":"c","n":"Good Times","c":0,"co":0,"cu":3,"t":1,"s":2,"b":0,"ch":40,"la":39.70,"lo":-104.95},
          {"id":"d","n":"Green Chile Shack","c":0,"co":0,"cu":1,"t":0,"s":1,"a":"200 E Colfax Ave","la":39.74,"lo":-104.98},
          {"id":"e","n":"Kum & Go","c":5,"co":5,"cu":4,"t":1,"s":1,"v":1,"la":38.83,"lo":-104.82},
          {"id":"f","n":"Royal Gorge Brew Pub","c":3,"co":3,"cu":0,"t":2,"s":0,"a":"413 Main St","la":38.44,"lo":-105.24,"j":3,"g":2,"liq":"Brew Pub"},
          {"id":"g","n":"Pearl Street Diner","c":2,"co":2,"cu":4,"t":2,"s":1,"a":"1100 Pearl St","la":40.018,"lo":-105.279,"j":2,
           "in":{"r":1,"p":62,"d":"2026-06-02","n":2,"rr":1,"cl":0,"h":[{"d":"2026-06-02","r":1,"p":62,"t":"Routine"},{"d":"2025-10-01","r":0,"p":12,"t":"Routine"}]}},
          {"id":"h","n":"Boulder Cafe","c":2,"co":2,"cu":4,"t":2,"s":1,"a":"1200 Pearl St","la":40.019,"lo":-105.278,"j":2,
           "in":{"r":2,"p":20,"d":"2026-05-01","n":1,"rr":0,"cl":1,"h":[{"d":"2026-05-01","r":2,"p":20,"t":"Routine"}]}},
          {"id":"i","n":"The Wolf's Tailor","c":0,"co":0,"cu":4,"t":2,"s":1,"hc":1,"a":"4058 Tejon St","la":39.773,"lo":-105.011,"j":3,"h":2,"mi":4,"ip":69,
           "jbf":"Outstanding Restaurateur winner 2024 (Erika Whitaker and Kelly Whitaker, ID EST)"},
          {"id":"j","n":"Ajax Tavern","c":4,"co":4,"cu":0,"t":1,"s":1,"hc":1,"a":"685 E Durant Ave","la":39.186,"lo":-106.818,"g":40,"seas":"winter, ski season"},
          {"id":"k","n":"Undated Deli","c":2,"co":2,"cu":4,"t":2,"s":1,"a":"1300 Pearl St","la":40.02,"lo":-105.277,"j":2,
           "in":{"r":0,"p":10,"d":null,"n":1,"rr":0,"cl":0,"h":[{"d":null,"r":0,"p":10,"t":"Routine"}]}},
          {"id":"l","n":"Same Day Diner","c":2,"co":2,"cu":4,"t":2,"s":1,"a":"1400 Pearl St","la":40.021,"lo":-105.276,"j":2,
           "in":{"r":0,"p":30,"d":"2026-04-17","n":2,"rr":1,"cl":0,"h":[{"d":"2026-04-17","r":0,"p":30,"t":"Re-Inspection"},{"d":"2026-04-17","r":1,"p":70,"t":"Routine"}]}},
          {"id":"m","n":"Old Format Brewing","c":5,"co":5,"cu":0,"t":2,"s":1,"a":"10 S Tejon St","la":38.833,"lo":-104.823,"j":3,
           "lic":[{"src":"Colorado liquor license","id":"03-11111","type":"Manufacturer (brewery)","exp":"2026-05-01"}]},
          {"id":"n","n":"Corner Liquor","c":5,"co":5,"cu":4,"t":2,"s":0,"v":1,"a":"20 S Tejon St","la":38.832,"lo":-104.823,"j":3,
           "lic":[{"src":"Colorado liquor license","id":"03-22222","type":"Retail Liquor Store","exp":null}]}
         ]}
        """
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("places-test.json")
        try json.data(using: .utf8)!.write(to: url)
        let model = AppModel(defaults: UserDefaults(suiteName: "test-\(UUID().uuidString)")!)
        await model.load(from: url)
        XCTAssertTrue(model.isLoaded, model.loadError ?? "")
        return model
    }

    func testDecodesAndHidesNonRestaurantsByDefault() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.places.count, 14)
        XCTAssertEqual(m.inspectionsThrough, "2026-07-21")
        let all = m.list(.all, sort: .name, search: "", here: nil)
        XCTAssertFalse(all.contains { $0.name == "Kum & Go" }, "gas-station counters are hidden unless asked for")
        m.filters.includeNonRestaurants = true
        XCTAssertTrue(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Kum & Go" })
    }

    func testGuidesListOnlyWhatTheyPromise() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.greenChile, sort: .name, search: "", here: nil).map(\.id), ["b"],
                       "a listing merely named \u{201C}Green Chile\u{201D} isn't hand-checked, so it stays out of the guide")
        XCTAssertEqual(m.list(.all, sort: .name, search: "green chile shack", here: nil).map(\.id), ["d"], "but it's still in the directory")
        XCTAssertEqual(m.list(.brewpubs, sort: .name, search: "", here: nil).map(\.id), ["f"], "brewpubs come from the state Brew Pub license")
        XCTAssertEqual(m.list(.game, sort: .name, search: "", here: nil).map(\.id), ["a"])
        XCTAssertEqual(m.list(.skiTowns, sort: .name, search: "", here: nil).map(\.id), ["j"])
        XCTAssertEqual(Set(m.list(.honors, sort: .iconic, search: "", here: nil).map(\.id)), ["i"])
        XCTAssertEqual(m.list(.oldest, sort: .oldest, search: "", here: nil).map(\.id), ["a"])
        XCTAssertEqual(m.list(.nearMe, sort: .nearest, search: "", here: nil), [], "near me needs a location")
    }

    func testOfficialInspectionResultsAreReadAsRecorded() async throws {
        let m = try await sampleModel()
        let cafe = m.place(id: "h")!
        XCTAssertEqual(cafe.inspection?.r, .closure, "a Closure at 20 points stays a Closure: the result is never derived from the points")
        XCTAssertEqual(cafe.inspection?.p, 20)
        XCTAssertEqual(m.list(.inspections, sort: .recent, search: "", here: nil).map(\.id), ["g", "h", "l", "k"],
                       "latest inspection first, and one without a published date after every dated one")
        XCTAssertEqual(m.list(.inspections, sort: .mostPoints, search: "", here: nil).map(\.id), ["g", "l", "h", "k"])
        XCTAssertEqual(m.list(.inspections, sort: .fewestPoints, search: "", here: nil).map(\.id), ["k", "h", "l", "g"])
        XCTAssertEqual(InspectionResult.reinspection.label, "Re-Inspection Required")
    }

    /// Boulder County's September 2025 system move stamped records without their date: null, never "inspected 2025-09-03".
    /// A routine inspection and its same-day re-inspection are two entries.
    func testUndatedAndSameDayInspections() async throws {
        let m = try await sampleModel()
        let undated = m.place(id: "k")!.inspection!
        XCTAssertNil(undated.d)
        XCTAssertNil(undated.h.first?.d)
        XCTAssertNil(DayFormat.text(undated.d), "no date to show, so the view says \u{201C}date not published\u{201D}")
        let sameDay = m.place(id: "l")!.inspection!
        XCTAssertEqual(sameDay.h.count, 2)
        XCTAssertEqual(sameDay.h.map(\.t), ["Re-Inspection", "Routine"])
        XCTAssertEqual(Set(sameDay.h.compactMap(\.d)), ["2026-04-17"])
    }

    /// Calendar days stay the same day in every time zone, and read as dates, not ISO strings.
    func testDatesAreCalendarDays() {
        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(identifier: "UTC")!
        let d = DayFormat.date("2026-06-16")!
        XCTAssertEqual(utc.dateComponents([.year, .month, .day], from: d), DateComponents(year: 2026, month: 6, day: 16))
        let text = DayFormat.text("2026-06-16")!
        XCTAssertTrue(text.contains("16") && text.contains("2026") && !text.contains("2026-06"), text)
        XCTAssertTrue(DayFormat.monthYear("2025-09-04")!.contains("2025"))
        XCTAssertNil(DayFormat.text(nil))
        XCTAssertEqual(DayFormat.text("soon"), "soon", "a value that isn't a date is shown as it is")
        XCTAssertNil(DayFormat.date("2026-13-01"))
        let boston = CLLocation(latitude: 42.3601, longitude: -71.0589), denver = CLLocation(latitude: 39.7439, longitude: -104.9926)
        let mi = Int((boston.distance(from: denver) / 1609.344).rounded())
        XCTAssertEqual(boston.milesText(to: denver), mi.formatted() + " mi", "miles are grouped for the reader's locale (\u{201C}1,760 mi\u{201D})")
        XCTAssertEqual(denver.milesText(to: denver), 0.0.formatted(.number.precision(.fractionLength(1))) + " mi")
    }

    /// "Serves alcohol" names the license, says when only a store license matched, and never reads as "no".
    func testServesAlcohol() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.place(id: "a")!.servesAlcohol, "Yes · Hotel & Restaurant license")
        XCTAssertEqual(m.place(id: "m")!.servesAlcohol, "Yes · Manufacturer (brewery) license", "a brewery's taproom serves on site")
        XCTAssertEqual(m.place(id: "n")!.servesAlcohol, "Store license only")
        XCTAssertEqual(m.place(id: "d")!.servesAlcohol, "Unknown (no state liquor license matched)")
        XCTAssertFalse(m.places.contains { $0.servesAlcohol.hasPrefix("—") })
    }

    func testHonorsAreFactsWithTheirOwnLabels() async throws {
        let m = try await sampleModel()
        let wolf = m.place(id: "i")!
        XCTAssertEqual(wolf.michelin.label, "2 MICHELIN Stars")
        XCTAssertEqual(wolf.jamesBeardLabel, "James Beard winner")
        XCTAssertTrue(wolf.isHonored)
        XCTAssertNil(m.place(id: "b")!.michelin.label)
        XCTAssertEqual(m.place(id: "a")!.liquor, "Hotel & Restaurant")
        XCTAssertNil(m.place(id: "d")!.liquor, "no license matched means unknown, never \u{201C}no\u{201D}")
    }

    func testNearestSort() async throws {
        let m = try await sampleModel()
        let denver = CLLocation(latitude: 39.7439, longitude: -104.9926)
        let near = m.list(.nearMe, sort: .nearest, search: "", here: denver)
        XCTAssertEqual(near.first?.id, "d", "the Colfax place is closest to downtown Denver")
        let ids = near.map(\.id)
        XCTAssertLessThan(ids.firstIndex(of: "g")!, ids.firstIndex(of: "j")!, "Boulder comes before Aspen")
    }

    func testSearchWordStartsAccentsTownsAndDishes() async throws {
        let m = try await sampleModel()
        func ids(_ q: String) -> [String] { m.list(.all, sort: .name, search: q, here: nil).map(\.id) }
        XCTAssertEqual(ids("buckhorn"), ["a"])
        XCTAssertTrue(ids("uckhorn").isEmpty, "matches the start of words only")
        XCTAssertEqual(ids("grays"), ["b"], "apostrophes don't matter")
        XCTAssertEqual(ids("canon city"), ["f"], "Cañon City without the tilde")
        XCTAssertEqual(ids("cañon city"), ["f"])
        XCTAssertEqual(ids("east colfax avenue"), ["d"], "east/avenue match the abbreviated address")
        XCTAssertEqual(ids("slopper"), ["b"], "a hand-checked dish is searchable")
        XCTAssertNil(Search.parse("slopper", towns: [:]).tag, "\u{201C}slopper\u{201D} is a dish, not the whole green chile guide")
        XCTAssertEqual(ids("pueblo green chile"), ["b"])
        XCTAssertEqual(ids("elk"), ["a"])
        XCTAssertEqual(ids("brewpub"), ["f"])
        XCTAssertEqual(ids("pitkin county"), ["j"], "the county is searchable")
        XCTAssertEqual(ids("🍕"), [], "nothing searchable typed means no results, not everything")
        XCTAssertEqual(ids("!!! ?"), [])
    }

    func testFiltersSavedPlacesAndMatchRates() async throws {
        let m = try await sampleModel()
        m.filters.hideChains = true
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Good Times" })
        m.filters = Filters(confirmedOnly: true)
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.id == "d" }, "single listings drop out")
        m.filters = Filters(town: "Boulder")
        XCTAssertEqual(Set(m.list(.all, sort: .name, search: "", here: nil).map(\.id)), ["g", "h", "k", "l"])
        m.filters = Filters()
        let p = m.place(id: "b")!
        m.toggleSaved(p)
        XCTAssertEqual(m.savedPlaces.map(\.id), ["b"])
        m.toggleSaved(p)
        XCTAssertTrue(m.savedPlaces.isEmpty)
        XCTAssertEqual(m.matchRate(for: m.place(id: "j")!), "71–76%")
        XCTAssertNil(m.matchRate(for: m.place(id: "a")!), "places on an official record don't cite a listing rate")
        XCTAssertEqual(m.place(id: "a")!.tier, .licensed)
    }

    func testListCacheFollowsFiltersSearchAndLocation() async throws {
        let m = try await sampleModel()
        let all = m.list(.all, sort: .name, search: "", here: nil)
        XCTAssertTrue(all.contains { $0.name == "Good Times" })
        m.filters.hideChains = true
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Good Times" }, "a filter change isn't served from the cache")
        m.filters = Filters()
        XCTAssertEqual(m.list(.all, sort: .name, search: "", here: nil).map(\.id), all.map(\.id))
        XCTAssertEqual(m.list(.all, sort: .name, search: "buckhorn", here: nil).map(\.id), ["a"])
        XCTAssertEqual(m.list(.all, sort: .name, search: "", here: nil).map(\.id), all.map(\.id))
        let denver = CLLocation(latitude: 39.7439, longitude: -104.9926), aspen = CLLocation(latitude: 39.19, longitude: -106.82)
        XCTAssertEqual(m.list(.nearMe, sort: .nearest, search: "", here: denver).first?.id, "d")
        XCTAssertEqual(m.list(.nearMe, sort: .nearest, search: "", here: aspen).first?.id, "j", "a new location isn't served from the cache")
    }

    func testNearMeIsntASearchWord() {
        let q = Search.parse("brewpub near me", towns: ["meeker": "Meeker"])
        XCTAssertEqual(q.tag, .brewpub)
        XCTAssertNil(q.town)
        XCTAssertTrue(q.tokens.isEmpty, "\"me\" mustn't match Meeker or Mexican places")
    }

    /// The one-pass normalize must agree with the regex version it replaced, on tricky strings and every bundled name and address.
    func testNormalizeMatchesTheRegexVersion() async throws {
        func reference(_ s: String) -> String {
            var t = s.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .init(identifier: "en_US")).lowercased()
            t = t.replacingOccurrences(of: #"\b([a-z0-9])\s*&\s*([a-z0-9])\b"#, with: "$1$2", options: .regularExpression)
            t = t.replacingOccurrences(of: "&", with: " and ")
            t = t.replacingOccurrences(of: #"['’`]"#, with: "", options: .regularExpression)
            t = t.replacingOccurrences(of: #"[^\p{L}\p{N}]+"#, with: " ", options: .regularExpression)
            return t.trimmingCharacters(in: .whitespaces)
        }
        for s in ["Gray's Coors Tavern", "B&B Cafe", "Rock & Roll Café", "  Phở 88!! ", "Snarf’s", "Joe`s", "A&W", "½ Price", "/pôr/ Wine House",
                  "#vybe", "Cañon City", "2400 E Colfax Ave #100", "🍕 Pizza", "Ⅻ Club", "", "---"] {
            XCTAssertEqual(Search.normalize(s), reference(s), s)
        }
        let m = AppModel(defaults: UserDefaults(suiteName: "norm-\(UUID().uuidString)")!)
        await m.load()
        for p in m.places {
            XCTAssertEqual(Search.normalize(p.name), reference(p.name), p.name)
            XCTAssertEqual(Search.normalize(p.fullAddress), reference(p.fullAddress), p.fullAddress)
        }
    }

    /// The real bundled file decodes and holds the guides the app promises.
    func testBundledData() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "bundle-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertGreaterThan(m.restaurantCount, 14_000)
        XCTAssertGreaterThan(m.count(.greenChile), 35)
        XCTAssertGreaterThan(m.count(.brewpubs), 150)
        XCTAssertGreaterThan(m.count(.honors), 80)
        XCTAssertGreaterThan(m.count(.inspections), 250)
        XCTAssertEqual(Set(m.places.map(\.id)).count, m.places.count, "ids are unique")
        // every place in a hand-checked guide is hand-checked
        for g in [Guide.greenChile, .game, .skiTowns] {
            XCTAssertTrue(m.places.filter(g.includes).allSatisfy(\.handChecked), "\(g.title) lists only hand-checked places")
        }
        // the research name is "El Taco de Mexico" since the Oct 7 rebuild; the honor is what's checked, not the capital D
        XCTAssertTrue(m.places.contains { $0.name.caseInsensitiveCompare("El Taco De Mexico") == .orderedSame && $0.jamesBeardLabel == "America's Classic" })
        XCTAssertTrue(m.places.contains { $0.name == "The Wolf's Tailor" && $0.michelin == .twoStars })
        XCTAssertTrue(m.list(.greenChile, sort: .name, search: "pueblo", here: nil).contains { $0.name.hasPrefix("Gray's") },
                      "the Pueblo slopper institution is in the green chile guide")
        // verified closed places are gone, whatever the map listings say
        XCTAssertFalse(m.places.contains { $0.name == "Q House" && $0.city == "Denver" })
        // no Google-derived data: the data file has no rating, review or price fields at all
        let raw = try String(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!, encoding: .utf8)
        for key in ["\"rating\"", "\"reviews\"", "\"price\"", "\"gmap_id\""] { XCTAssertFalse(raw.contains(key), "\(key) must not ship") }
    }

    /// The bundled data against the QA findings that reached the store listing: adult clubs, directory and news links, mangled
    /// towns and names, lapsed-looking license dates and inspections that aren't the place's own.
    func testBundledDataGuards() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "guards-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertEqual(DataGuards.adultVenues(m.places), [], "no place at a known strip club's address or under its name")
        XCTAssertEqual(DataGuards.badWebsites(m.places), [], "no directory, Google or news page as a restaurant's website")
        XCTAssertEqual(DataGuards.badTowns(m.places), [], "no town cut short (\u{201C}Fris\u{201D} for Frisco, \u{201C}Ri\u{201D} for Rico)")
        XCTAssertEqual(DataGuards.badNames(m.places), [], "no visible name ending in \u{201C} the\u{201D} or \u{201C} of\u{201D}, or just \u{201C}The\u{201D}")
        XCTAssertEqual(DataGuards.lapsedExpiries(m.places, listDate: m.liquorUpdated), [], "no license expiry before the active list's own date")
        XCTAssertEqual(DataGuards.inspectionsOutsideBoulderCounty(m.places), [], "inspections are Boulder County's own")
        XCTAssertFalse(m.places.contains { $0.name == "GQue BBQ" && $0.city == "Westminster" && $0.inspection != nil },
                       "a food truck's event inspection in Boulder County isn't the Westminster restaurant's")
        XCTAssertEqual(DataGuards.nonRestaurants(m.places), [], "no nail salon, senior home, gun store or gas station among the restaurants")
        // QA gap round: Coma carried Pony M Cake's inspection at their shared address, matched through the fragment "M" that
        // deleting the accent in "Méxican" left behind
        XCTAssertFalse(m.places.contains { $0.name == "Coma M\u{00E9}xican Grill" && $0.inspection?.p == 100 },
                       "Coma M\u{00E9}xican Grill shows Pony M Cake's 100-point inspection")
    }

    /// Each guard above fires on a copy of the bundled data broken the way QA found it: a guard that can't fail guards nothing
    /// (the old website check had double backslashes in a raw string and matched nothing).
    func testGuardsCatchABrokenCopy() async throws {
        let raw = try Data(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!)
        var file = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        var places = try XCTUnwrap(file["places"] as? [[String: Any]])
        var cities = try XCTUnwrap(file["cities"] as? [String])
        let counties = try XCTUnwrap(file["counties"] as? [String])
        cities.append("Fris")
        // six ordinary visible places, each broken one way
        let idx = places.indices.filter { places[$0]["v"] == nil }.prefix(8).map { $0 }
        places[idx[0]]["w"] = "https://www.yelp.com/biz/some-place"
        places[idx[1]]["w"] = "https://www.westword.com/restaurants/a-story-123"
        places[idx[2]]["a"] = "490 South Colorado Boulevard"
        places[idx[3]]["c"] = cities.count - 1
        places[idx[4]]["n"] = "Kitchen the"
        places[idx[5]]["lic"] = [["src": "Colorado liquor license", "id": "03-00000", "type": "Tavern", "exp": "2014-05-16"]]
        places[idx[6]]["co"] = try XCTUnwrap(counties.firstIndex(of: "Denver"))
        places[idx[6]]["in"] = ["r": 0, "p": 4, "d": "2026-05-01", "n": 1, "rr": 0, "cl": 0, "h": [["d": "2026-05-01", "r": 0, "p": 4, "t": "Routine"]]]
        places[idx[7]]["n"] = "Tipsy Nails & Spa"
        file["places"] = places
        file["cities"] = cities
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("places-broken.json")
        try JSONSerialization.data(withJSONObject: file).write(to: url)
        let m = AppModel(defaults: UserDefaults(suiteName: "broken-\(UUID().uuidString)")!)
        await m.load(from: url)
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        let id = idx.map { places[$0]["id"] as? String }
        func caught(_ found: [String], _ i: Int, _ what: String) {
            XCTAssertTrue(found.contains { $0.contains("[\(id[i] ?? "?")]") }, "the guard missed \(what)")
        }
        caught(DataGuards.badWebsites(m.places), 0, "a Yelp page")
        caught(DataGuards.badWebsites(m.places), 1, "a Westword story")
        caught(DataGuards.adultVenues(m.places), 2, "490 South Colorado Boulevard (= 490 S Colorado Blvd)")
        XCTAssertTrue(DataGuards.badTowns(m.places).contains("Fris"), "the guard missed \u{201C}Fris\u{201D}")
        caught(DataGuards.badNames(m.places), 4, "\u{201C}Kitchen the\u{201D}")
        caught(DataGuards.lapsedExpiries(m.places, listDate: m.liquorUpdated), 5, "a 2014 expiry")
        caught(DataGuards.inspectionsOutsideBoulderCounty(m.places), 6, "a Denver place with an inspection")
        caught(DataGuards.nonRestaurants(m.places), 7, "a nail salon shown as a restaurant")
    }
}

/// Checks on the bundled data, written as functions so testGuardsCatchABrokenCopy can prove each one fires.
enum DataGuards {
    /// directories, Google and news sites (QA AR-8): matched on the link's host, so "smart.com" isn't "rt.com"
    static let badHosts = #"^https?://([^/?#]*\.)?(yelp\.com|business\.site|google\.com|groupon\.com|yellowpages\.com|westword\.com|eater\.com|dailycamera\.com|rt\.com|denverpost\.com)([:/?#]|$)"#

    static func badWebsites(_ places: [Place]) -> [String] {
        places.compactMap { p in
            guard let w = p.website?.absoluteString, w.range(of: badHosts, options: [.regularExpression, .caseInsensitive]) != nil else { return nil }
            return "\(p.name) [\(p.id)]: \(w)"
        }
    }

    /// Strip clubs QA found behind plain trade names on ordinary Tavern licenses, by street address (a town only where the
    /// street number repeats elsewhere) and by name.
    static let adultAddresses: [(address: String, town: String?)] = [
        ("490 S Colorado Blvd", nil), ("4451 E Virginia Ave", nil), ("1601 W Evans Ave", nil), ("214 S Federal Blvd", nil),
        ("511 W Colfax Ave", nil), ("1124 Pearl St", "Boulder"), ("7950 N Federal Blvd", nil), ("6710 N Federal Blvd", nil),
        ("5975 Terminal Ave", nil), ("4630 Austin Bluffs Pkwy", nil), ("2258 Colex Dr", nil),
    ]
    static let adultNames = #"shotgun willie|\bpt['’]?s\b|scarlett['’]?s|diamond cabaret|gentlem[ae]n['’]?s club|strip club|exotic dancer|cabaret"#

    static func adultVenues(_ places: [Place]) -> [String] {
        // "490 South Colorado Boulevard" and "490 S Colorado Blvd" are the same address: street words abbreviated, case and punctuation gone
        let wanted = adultAddresses.map { (Search.normalizeAddress($0.address), $0.town) }
        return places.compactMap { p in
            let a = Search.normalizeAddress(p.address ?? "")
            let atAddress = !a.isEmpty && wanted.contains { $0.0 == a && ($0.1 == nil || $0.1 == p.city) }
            let named = p.name.range(of: adultNames, options: [.regularExpression, .caseInsensitive]) != nil
            return atAddress || named ? "\(p.name) [\(p.id)], \(p.address ?? "")" : nil
        }
    }

    /// every town at least three letters, and not one of the two QA found cut short
    static func badTowns(_ places: [Place]) -> [String] {
        Set(places.compactMap(\.city)).filter { t in ["Fris", "Ri"].contains(t) || t.filter(\.isLetter).count < 3 }.sorted()
    }

    /// a name cut off after "the" or "of" ("Kitchen the", "Wines of") or nothing but "The", among the places shown by default
    static func badNames(_ places: [Place]) -> [String] {
        places.filter { p in
            let n = p.name.trimmingCharacters(in: .whitespaces).lowercased()
            return !p.isVenue && (n.hasSuffix(" the") || n.hasSuffix(" of") || n == "the")
        }.map { "\($0.name) [\($0.id)]" }
    }

    /// a liquor license expiry before the state's active list was published reads as lapsed (renewals pending stay on the list)
    static func lapsedExpiries(_ places: [Place], listDate: String) -> [String] {
        places.flatMap { p in p.licenses.compactMap { l in l.exp.flatMap { $0 < listDate ? "\(p.name) [\(p.id)]: \(l.id) \($0)" : nil } } }
    }

    /// businesses that hold a beer-and-wine license but aren't places to eat (QA gap round: nail bars, senior homes, a gun store,
    /// gas stations), among the places shown by default
    static let nonRestaurantNames = #"\bnails?\b|\bsenior\b|assisted living|\bguns?\b|firearms|petroleum|\bsinclair\b|living spaces"#

    static func nonRestaurants(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: nonRestaurantNames, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }

    /// only Boulder County publishes inspections, so a result anywhere else came from another business's record
    static func inspectionsOutsideBoulderCounty(_ places: [Place]) -> [String] {
        places.filter { $0.inspection != nil && $0.county != "Boulder County" }.map { "\($0.name) [\($0.id)], \($0.city ?? "")" }
    }
}
