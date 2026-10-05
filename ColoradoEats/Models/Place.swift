import Foundation
import CoreLocation
import SwiftUI

// MARK: - The bundled data file (Resources/places.json), written by pipeline/colorado.py with CO_APP=1

struct DataFile: Decodable {
    let generated: String
    let inspections_through: String
    let inspections_published: String
    let liquor_updated: String
    let cities: [String]
    let cuisines: [String]
    let brands: [String]
    let counties: [String]
    let srcs: [String]
    let count_restaurants: Int
    let calibration: [String: CalibrationArea]
    let places: [PlaceRecord]
}

/// How often listings of one kind matched an official record in Denver and Boulder County (pipeline/calibrate.py).
struct CalibrationArea: Decodable, Hashable {
    let listings: Int
    let official_records: Int
    let groups: [String: CalibrationGroup]
}

struct CalibrationGroup: Decodable, Hashable {
    let n: Int
    let official: Double
}

/// Colorado's inspection rating (CDPHE Interpretive Memo 19-09): read from the record, never computed from the points.
enum InspectionResult: Int, Decodable, Hashable {
    case pass = 0, reinspection = 1, closure = 2

    var label: String {
        switch self {
        case .pass: "Pass"
        case .reinspection: "Re-Inspection Required"
        case .closure: "Closure"
        }
    }
    var fill: Color {
        switch self {
        case .pass: Color(hex: 0xDDEFE3)
        case .reinspection: Color(hex: 0xFFE9C2)
        case .closure: Color(hex: 0xF9D5DB)
        }
    }
    var ink: Color {
        switch self {
        case .pass: Color(hex: 0x0E5A2B)
        case .reinspection: Color(hex: 0x6B3A00)
        case .closure: Color(hex: 0x7A0019)
        }
    }
}

struct InspectionVisit: Decodable, Hashable {
    let d: String           // date
    let r: InspectionResult // official result
    let p: Int              // risk points (lower is better)
    let t: String           // Routine or Re-Inspection
}

/// Boulder County Public Health's inspections since September 2025, latest first.
struct InspectionRecord: Decodable, Hashable {
    let r: InspectionResult // result at the latest inspection
    let p: Int              // risk points at the latest inspection
    let d: String           // latest inspection date
    let n: Int              // inspections since Sep 2025
    let rr: Int             // of those, Re-Inspection Required
    let cl: Int             // of those, Closure
    let h: [InspectionVisit]
    let i: [String]?        // code sections cited at the latest inspection
}

/// An official record behind a place: a Denver business license or a state liquor license.
struct LicenseRecord: Decodable, Hashable {
    let src: String
    let id: String
    let type: String?
    let exp: String?
}

struct PlaceRecord: Decodable {
    let id: String
    let n: String
    let c: Int?
    let cu: Int
    let t: Int
    let s: Int
    let co: Int?
    let a: String?
    let z: String?
    let la: Double?
    let lo: Double?
    let b: Int?
    let ch: Int?
    let j: Int?
    let v: Int?
    let bar: Int?
    let g: Int?
    let hc: Int?
    let h: Int?
    let mi: Int?
    let jbf: String?
    let ip: Double?
    let f: Int?
    let fn: String?
    let note: String?
    let dish: String?
    let seas: String?
    let liq: String?
    let w: String?
    let ph: String?
    let lic: [LicenseRecord]?
    let inspection: InspectionRecord?

    enum CodingKeys: String, CodingKey {
        case id, n, c, cu, t, s, co, a, z, la, lo, b, ch, j, v, bar, g, hc, h, mi, jbf, ip, f, fn, note, dish, seas, liq, w, ph, lic
        case inspection = "in"
    }
}

// MARK: - The model the views use

struct PlaceTags: OptionSet, Hashable {
    let rawValue: Int
    static let greenChile = PlaceTags(rawValue: 1)    // hand-checked
    static let brewpub = PlaceTags(rawValue: 2)       // holds a state Brew Pub or Distillery Pub license
    static let game = PlaceTags(rawValue: 4)          // hand-checked game or steakhouse
    static let skiTown = PlaceTags(rawValue: 8)       // any place in a ski town
    static let oldest = PlaceTags(rawValue: 16)       // hand-checked, open at this address since 1960 or earlier
    static let skiDining = PlaceTags(rawValue: 32)    // hand-checked ski-town dining
}

/// How a place got on the list. The share that matched an official record comes from calibration.
enum Tier: Int, Comparable {
    case listing = 0        // one map listing
    case confirmed = 1      // a high-confidence Meta listing, or a hand-checked place
    case licensed = 2       // on an official record: a Denver license, a state liquor license or a Boulder County inspection

    static func < (a: Tier, b: Tier) -> Bool { a.rawValue < b.rawValue }

    var label: String {
        switch self {
        case .licensed: "On an official record"
        case .confirmed: "Confirmed listing"
        case .listing: "Listing only"
        }
    }
}

enum Jurisdiction: Int {
    case none = 0, denver = 1, boulder = 2, liquor = 3
    var listName: String {
        switch self {
        case .denver: "City and County of Denver business licenses"
        case .boulder: "Boulder County Public Health inspection records"
        case .liquor: "Colorado liquor licenses (Department of Revenue)"
        case .none: ""
        }
    }
}

enum Michelin: Int {
    case none = 0, recommended = 1, bib = 2, oneStar = 3, twoStars = 4, threeStars = 5
    var label: String? {
        switch self {
        case .none: nil
        case .recommended: "MICHELIN Recommended"
        case .bib: "Bib Gourmand"
        case .oneStar: "1 MICHELIN Star"
        case .twoStars: "2 MICHELIN Stars"
        case .threeStars: "3 MICHELIN Stars"
        }
    }
}

struct Place: Identifiable, Hashable {
    let id: String
    let name: String
    let address: String?
    let city: String?
    let county: String?
    let zip: String?
    let coordinate: CLLocationCoordinate2D?
    let cuisine: String
    let brand: String?
    let chainCount: Int
    let tier: Tier
    let jurisdiction: Jurisdiction
    let source: String
    let isVenue: Bool
    let isBar: Bool
    let tags: PlaceTags
    /// On our hand-checked list (data/research): confirmed open with a 2025–26 source.
    let handChecked: Bool
    let honorFlags: Int
    let michelin: Michelin
    let iconicPoints: Double?
    let jamesBeard: String?
    let founded: Int?
    let foundedNote: String?
    let note: String?
    let dishes: String?
    let seasonal: String?
    /// on-premises state liquor license type ("Hotel & Restaurant", "Brew Pub"); nil means unknown, not "no"
    let liquor: String?
    let website: URL?
    let phone: String?
    let licenses: [LicenseRecord]
    let inspection: InspectionRecord?
    /// normalized text for search: name, town, county, zip, cuisine, brand, dishes, then the address with street words abbreviated
    let searchText: String
    let nameText: String

    static func == (a: Place, b: Place) -> Bool { a.id == b.id }
    func hash(into h: inout Hasher) { h.combine(id) }

    var isHonored: Bool { honorFlags != 0 || michelin != .none }
    var isChain: Bool { chainCount >= 5 }
    var jamesBeardLabel: String? {
        if honorFlags & 1 != 0 { return "America's Classic" }
        if honorFlags & 2 != 0 { return "James Beard winner" }
        if honorFlags & 4 != 0 { return "James Beard finalist" }
        if honorFlags & 8 != 0 { return "James Beard semifinalist" }
        return nil
    }
    var townLine: String { [city, cuisine].compactMap { $0 }.joined(separator: " · ") }
    var fullAddress: String {
        [address, [city, zip].compactMap { $0 }.joined(separator: " ")].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
    }
    var location: CLLocation? { coordinate.map { CLLocation(latitude: $0.latitude, longitude: $0.longitude) } }

    init(_ r: PlaceRecord, file: DataFile) {
        let city = r.c.flatMap { $0 < file.cities.count ? file.cities[$0] : nil }
        let cuisine = r.cu < file.cuisines.count ? file.cuisines[r.cu] : "American & Other"
        let brand = r.b.flatMap { $0 < file.brands.count ? file.brands[$0] : nil }
        let county = r.co.flatMap { $0 < file.counties.count ? file.counties[$0] : nil }
        id = r.id
        name = r.n
        address = r.a
        self.city = city
        self.county = county
        zip = r.z
        if let la = r.la, let lo = r.lo { coordinate = CLLocationCoordinate2D(latitude: la, longitude: lo) } else { coordinate = nil }
        self.cuisine = cuisine
        self.brand = brand
        chainCount = r.ch ?? 1
        tier = Tier(rawValue: r.t) ?? .listing
        jurisdiction = Jurisdiction(rawValue: r.j ?? 0) ?? .none
        source = r.s < file.srcs.count ? file.srcs[r.s] : "meta"
        isVenue = r.v == 1
        isBar = r.bar == 1
        tags = PlaceTags(rawValue: r.g ?? 0)
        handChecked = r.hc == 1
        honorFlags = r.h ?? 0
        michelin = Michelin(rawValue: r.mi ?? 0) ?? .none
        iconicPoints = r.ip
        jamesBeard = r.jbf
        founded = r.f
        foundedNote = r.fn
        note = r.note
        dishes = r.dish
        seasonal = r.seas
        liquor = r.liq
        website = r.w.flatMap { URL(string: $0.hasPrefix("http") ? $0 : "https://" + $0) }
        phone = r.ph
        licenses = r.lic ?? []
        inspection = r.inspection
        // the dishes a hand-checked place serves are searchable too: "slopper pueblo", "elk"
        searchText = " " + Search.normalize([r.n, city, county, r.z, cuisine, brand, r.dish].compactMap { $0 }.joined(separator: " ")) + " "
            + Search.normalizeAddress(r.a ?? "") + " "
        nameText = " " + Search.normalize([r.n, brand].compactMap { $0 }.joined(separator: " ")) + " "
    }
}
