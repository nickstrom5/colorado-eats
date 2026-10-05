import CoreSpotlight
import UniformTypeIdentifiers

/// Puts the hand-checked and honored places (green chile spots, ski-town dining, MICHELIN and James Beard places, the oldest ones)
/// into iPhone search, so "green chile pueblo" in Spotlight can open the place in the app.
enum SpotlightIndexer {
    static let domain = "places"
    private static let versionKey = "spotlightIndexedGenerated"

    static func indexIfNeeded(_ places: [Place], generated: String, defaults: UserDefaults = .standard) {
        guard CSSearchableIndex.isIndexingAvailable(), defaults.string(forKey: versionKey) != generated else { return }
        let featured = places.filter { !$0.isVenue && ($0.isHonored || $0.handChecked) && !$0.isChain }
        let items = featured.map { p -> CSSearchableItem in
            let attrs = CSSearchableItemAttributeSet(contentType: .content)
            attrs.title = p.name
            var kinds: [String] = []
            if p.tags.contains(.greenChile) { kinds.append("Green chile") }
            if p.tags.contains(.game) { kinds.append("Game & steak") }
            if p.tags.contains(.skiDining) { kinds.append("Ski town dining") }
            if p.tags.contains(.brewpub) { kinds.append("Brewpub") }
            if let m = p.michelin.label { kinds.append(m) }
            if let jb = p.jamesBeardLabel { kinds.append(jb) }
            attrs.contentDescription = ([kinds.joined(separator: " · ")] + [p.fullAddress]).filter { !$0.isEmpty }.joined(separator: "\n")
            attrs.keywords = kinds + [p.city, p.cuisine, "Colorado"].compactMap { $0 }
            if let c = p.coordinate { attrs.latitude = NSNumber(value: c.latitude); attrs.longitude = NSNumber(value: c.longitude); attrs.supportsNavigation = true }
            return CSSearchableItem(uniqueIdentifier: p.id, domainIdentifier: domain, attributeSet: attrs)
        }
        CSSearchableIndex.default().deleteSearchableItems(withDomainIdentifiers: [domain]) { _ in
            CSSearchableIndex.default().indexSearchableItems(items) { error in
                if error == nil { defaults.set(generated, forKey: versionKey) }
            }
        }
    }
}
