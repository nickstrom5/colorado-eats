import Foundation
import CoreLocation
import UIKit

/// `-screenshot <name>` opens one screen with fixed state for App Store screenshots (scripts/capture-screenshots.sh).
/// Names: home, greenchile, brewpubs, ski, detail, map, honors, oldest, saved, about.
enum ScreenshotMode {
    /// Debug builds only: an App Store build ignores the launch argument, so no one can reach seeded screens or fake locations.
    static var name: String? {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-screenshot"), i + 1 < args.count else { return nil }
        return args[i + 1]
        #else
        return nil
        #endif
    }
    static var isActive: Bool { name != nil }

    @MainActor
    static func apply(to model: AppModel) {
        guard let name, model.isLoaded else { return }
        model.filters = Filters()
        // downtown Denver, so "nearest" lists have distances without a permission prompt
        model.screenshotLocation = CLLocation(latitude: 39.7439, longitude: -104.9926)
        let pick = { (n: String) in model.places.first { $0.name == n } }
        for n in ["Buckhorn Exchange", "Gray's Coors Tavern", "El Taco De Mexico", "The Wolf's Tailor"] {
            if let p = pick(n), !model.isSaved(p) { model.toggleSaved(p) }
        }
        let open = { (g: Guide) in model.tab = .guides; model.selectedGuide = g; model.guidesPath = [.guide(g)] }
        switch name {
        case "greenchile": open(.greenChile)
        case "brewpubs": open(.brewpubs)
        case "ski": open(.skiTowns)
        case "honors": open(.honors)
        case "oldest": open(.oldest)
        case "detail":
            open(.oldest)
            if let p = pick("Buckhorn Exchange") ?? model.places.first { model.selectedPlace = p; model.guidesPath.append(.place(p)) }
        case "map": model.tab = .map
        case "saved": model.tab = .saved
        case "about": model.tab = .about
        default: model.tab = .guides; model.selectedGuide = nil
        }
        // iPad shows the place column next to every list, so give each shot a place instead of "Pick a place".
        guard UIDevice.current.userInterfaceIdiom == .pad, model.selectedPlace == nil else { return }
        let place: Place? = switch name {
        case "greenchile": pick("El Taco De Mexico")
        case "honors": pick("The Wolf's Tailor")
        case "ski": model.list(.skiTowns, sort: .featured, search: "", here: nil).first
        case "brewpubs": model.list(.brewpubs, sort: .name, search: "", here: nil).first
        case "saved": pick("Gray's Coors Tavern")
        case "about": nil
        default: pick("Buckhorn Exchange")
        }
        model.selectedPlace = place
    }
}
