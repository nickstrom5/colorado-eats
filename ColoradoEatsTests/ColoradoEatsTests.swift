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
          {"id":"j","n":"Ajax Tavern","c":4,"co":4,"cu":0,"t":1,"s":1,"hc":1,"a":"685 E Durant Ave","la":39.186,"lo":-106.818,"g":40,"seas":"winter, ski season"}
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
        XCTAssertEqual(m.places.count, 10)
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
        XCTAssertEqual(m.list(.inspections, sort: .recent, search: "", here: nil).map(\.id), ["g", "h"], "latest inspection first")
        XCTAssertEqual(m.list(.inspections, sort: .mostPoints, search: "", here: nil).map(\.id), ["g", "h"])
        XCTAssertEqual(m.list(.inspections, sort: .fewestPoints, search: "", here: nil).map(\.id), ["h", "g"])
        XCTAssertEqual(InspectionResult.reinspection.label, "Re-Inspection Required")
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
        XCTAssertEqual(ids("slopper"), ["b"], "a hand-checked dish is searchable, and \u{201C}slopper\u{201D} means the green chile guide")
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
        XCTAssertEqual(Set(m.list(.all, sort: .name, search: "", here: nil).map(\.id)), ["g", "h"])
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
        XCTAssertTrue(m.places.contains { $0.name == "El Taco De Mexico" && $0.jamesBeardLabel == "America's Classic" })
        XCTAssertTrue(m.places.contains { $0.name == "The Wolf's Tailor" && $0.michelin == .twoStars })
        XCTAssertTrue(m.list(.greenChile, sort: .name, search: "pueblo", here: nil).contains { $0.name.hasPrefix("Gray's") },
                      "the Pueblo slopper institution is in the green chile guide")
        // verified closed places are gone, whatever the map listings say
        XCTAssertFalse(m.places.contains { $0.name == "Q House" && $0.city == "Denver" })
        XCTAssertFalse(m.places.contains { $0.name.range(of: #"gentlem[ae]n'?s club|strip club|exotic dancer|cabaret"#, options: [.regularExpression, .caseInsensitive]) != nil },
                       "adult clubs aren't restaurants")
        XCTAssertFalse(m.places.contains { ($0.website?.absoluteString ?? "").range(
            of: #"yelp\\.com|business\\.site|google\\.com|groupon\\.com|yellowpages\\.com"#, options: .regularExpression) != nil },
                       "directory links were checked out")
        // no Google-derived data: the data file has no rating, review or price fields at all
        let raw = try String(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!, encoding: .utf8)
        for key in ["\"rating\"", "\"reviews\"", "\"price\"", "\"gmap_id\""] { XCTAssertFalse(raw.contains(key), "\(key) must not ship") }
    }
}
