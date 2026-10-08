import Foundation
import CoreLocation

/// The lists the app is built around. Each is a filter plus an order; none uses ratings (the app only publishes data it may).
enum Guide: String, CaseIterable, Identifiable, Hashable {
    case greenChile, brewpubs, skiTowns, game, honors, oldest, inspections, nearMe, all

    var id: String { rawValue }

    var title: String {
        switch self {
        case .greenChile: "Green Chile"
        case .brewpubs: "Brewpubs"
        case .skiTowns: "Ski Town Dining"
        case .game: "Game & Steakhouses"
        case .honors: "MICHELIN & James Beard"
        case .oldest: "Oldest Places"
        case .inspections: "Inspections"
        case .nearMe: "Near Me"
        case .all: "All Restaurants"
        }
    }

    var subtitle: String {
        switch self {
        case .greenChile: "Hand-checked smothered burritos, Pueblo sloppers and chile by the bowl"
        case .brewpubs: "Places with a Colorado Brew Pub or Distillery Pub license"
        case .skiTowns: "Hand-checked dining in Aspen, Vail, Breckenridge, Telluride and more"
        case .game: "Bison, elk, trout and steak, hand-checked"
        case .honors: "MICHELIN Guide Colorado 2026 and James Beard honorees"
        case .oldest: "Founding years checked at the same address, oldest first"
        case .inspections: "Boulder County's official inspection results"
        case .nearMe: "Everything around you, closest first"
        case .all: "Restaurants, cafés, bars and bakeries statewide"
        }
    }

    var systemImage: String {
        switch self {
        case .greenChile: "flame"
        case .brewpubs: "mug"
        case .skiTowns: "mountain.2"
        case .game: "fork.knife.circle"
        case .honors: "star.circle"
        case .oldest: "clock.arrow.circlepath"
        case .inspections: "checkmark.seal"
        case .nearMe: "location"
        case .all: "fork.knife"
        }
    }

    /// The Colorado guides get the gold card on Home.
    var isColorado: Bool { [.greenChile, .brewpubs, .skiTowns, .game].contains(self) }

    /// Guides whose order is a ranking worth numbering.
    var isRanked: Bool { [.oldest].contains(self) }

    var sortOptions: [SortOrder] {
        switch self {
        case .greenChile, .game, .skiTowns: [.featured, .nearest, .name]
        case .brewpubs: [.name, .nearest]
        case .honors: [.iconic, .nearest]
        case .oldest: [.oldest]
        case .inspections: [.recent, .fewestPoints, .mostPoints, .nearest]
        case .nearMe: [.nearest]
        case .all: [.name, .nearest]
        }
    }

    var defaultSort: SortOrder { sortOptions[0] }

    func includes(_ p: Place) -> Bool {
        switch self {
        // the guides that promise "hand-checked" list only places checked open with a 2025–26 source
        case .greenChile: p.handChecked && p.tags.contains(.greenChile)
        case .game: p.handChecked && p.tags.contains(.game)
        case .skiTowns: p.handChecked && p.tags.contains(.skiDining)
        // a brewpub is a place holding the state's Brew Pub (or Distillery Pub) license: an official record
        case .brewpubs: p.tags.contains(.brewpub)
        case .honors: p.michelin != .none || p.jamesBeard != nil
        case .oldest: p.founded != nil
        case .inspections: p.inspection != nil
        case .nearMe, .all: true
        }
    }
}

enum SortOrder: String, CaseIterable, Identifiable {
    case featured, nearest, oldest, name, iconic, recent, fewestPoints, mostPoints
    var id: String { rawValue }
    var label: String {
        switch self {
        case .featured: "Featured first"
        case .nearest: "Nearest"
        case .oldest: "Oldest first"
        case .name: "A to Z"
        case .iconic: "MICHELIN, then James Beard"
        case .recent: "Latest inspection first"
        case .fewestPoints: "Fewest risk points"
        case .mostPoints: "Most risk points"
        }
    }
}

/// Filters shared by every list. Search text lives with each list.
struct Filters: Equatable, Codable {
    var town: String?
    var cuisine: String?
    var hideChains = false
    var confirmedOnly = false
    var includeNonRestaurants = false

    var activeCount: Int {
        [town != nil, cuisine != nil, hideChains, confirmedOnly, includeNonRestaurants].filter { $0 }.count
    }

    func allows(_ p: Place) -> Bool {
        if !includeNonRestaurants && p.isVenue { return false }
        if let town, p.city != town { return false }
        if let cuisine, p.cuisine != cuisine { return false }
        if hideChains && p.isChain { return false }
        if confirmedOnly && p.tier == .listing { return false }
        return true
    }
}

enum Ranking {
    static func sort(_ places: [Place], by order: SortOrder, from here: CLLocation?) -> [Place] {
        // Keys come from fields made once at load: a localized compare, or a new CLLocation per comparison, made a 16,000-place
        // sort take most of a second (AR-13). sortKey is the normalized name, so case, accents and punctuation don't change the order.
        func name(_ a: Place, _ b: Place) -> Bool { a.sortKey != b.sortKey ? a.sortKey < b.sortKey : a.id < b.id }
        switch order {
        case .nearest where here != nil:
            // each distance once, not four times per comparison
            let from = here!
            return places.map { p in (p, p.location.map { $0.distance(from: from) } ?? .greatestFiniteMagnitude) }
                .sorted { $0.1 != $1.1 ? $0.1 < $1.1 : name($0.0, $1.0) }
                .map(\.0)
        case .featured, .nearest:
            // honored places first, then verified founding year, then name
            return places.sorted {
                let a = $0.iconicPoints ?? -1, b = $1.iconicPoints ?? -1
                if a != b { return a > b }
                let fa = $0.founded ?? 9999, fb = $1.founded ?? 9999
                return fa != fb ? fa < fb : name($0, $1)
            }
        case .oldest:
            return places.sorted { ($0.founded ?? 9999) != ($1.founded ?? 9999) ? ($0.founded ?? 9999) < ($1.founded ?? 9999) : name($0, $1) }
        case .name:
            return places.sorted(by: name)
        case .iconic:
            // an order anyone can check: MICHELIN distinction, then the James Beard honor (America's Classic, winner, finalist, semifinalist), then name
            func jb(_ p: Place) -> Int { p.honorFlags & 1 != 0 ? 4 : p.honorFlags & 2 != 0 ? 3 : p.honorFlags & 4 != 0 ? 2 : p.honorFlags & 8 != 0 ? 1 : 0 }
            return places.sorted {
                if $0.michelin.rawValue != $1.michelin.rawValue { return $0.michelin.rawValue > $1.michelin.rawValue }
                if jb($0) != jb($1) { return jb($0) > jb($1) }
                return name($0, $1)
            }
        case .recent:
            // an inspection without a published date (the county's Sept 2025 system move) goes after every dated one
            return places.sorted {
                let a = $0.inspection?.d ?? "", b = $1.inspection?.d ?? ""
                return a != b ? a > b : name($0, $1)
            }
        case .fewestPoints, .mostPoints:
            let few = order == .fewestPoints
            return places.sorted {
                let a = $0.inspection?.p ?? 0, b = $1.inspection?.p ?? 0
                if a != b { return few ? a < b : a > b }
                return name($0, $1)
            }
        }
    }
}
