import SwiftUI

struct AboutView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("COLORADO EATS").displayFont(30).foregroundStyle(Theme.green)
                    Text("A free guide to \(model.restaurantCount.formatted()) Colorado restaurants, with hand-checked lists of green chile spots, game and steakhouses, ski-town dining and the state's oldest places, every brewpub with a state license, and Boulder County's official inspection results. No account, no ads, no tracking.")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                    Text("Colorado Eats (\u{201C}CO Eats\u{201D}) is an independent app by Nicholas Soderstrom. It is not affiliated with, endorsed by or operated by the State of Colorado, the Colorado Department of Revenue, the Colorado Department of Public Health and Environment, the City and County of Denver, Boulder County, the MICHELIN Guide, the James Beard Foundation, Apple, or any restaurant, team or chain.")
                        .font(.footnote).foregroundStyle(Theme.muted)
                }
                .padding(.vertical, 4)
            }
            Section("How the lists are built") {
                Text("Green chile, game and steakhouses, ski-town dining and the oldest places are hand-checked: each was checked in September and October 2026 against a 2025 or 2026 source (the place's own website or menu, or local news), with the address checked. Founding years mean the year it opened at this address.")
                Text("Brewpubs are the places holding a Colorado Brew Pub or Distillery Pub liquor license. Honors are the MICHELIN Guide Colorado 2026 selection and James Beard Foundation awards and nominations from 2023 to 2026.")
                Text("The rest come from Overture Maps' open place data, the City and County of Denver's active business licenses, the State of Colorado's active liquor licenses and Boulder County Public Health's inspected facilities. Map listings are kept only when they proved reliable: checked against Denver's licenses and Boulder County's inspections, high-confidence listings matched an official record \(rate("meta_high")) of the time. Website links are checked, and any that no longer belong to the place are left out.")
                Text("Inspection results are Boulder County's official results, shown as recorded (Pass, Re-Inspection Required or Closure) with their risk points. Other Colorado counties don't publish inspections in bulk, so they aren't here.")
                Text("Ratings, reviews, hours and photos are Apple Maps' own, shown live in Apple's place card. This app doesn't store or rank by them.")
            }
            .font(.subheadline).foregroundStyle(Theme.ink2)
            Section("Sources") {
                source("Overture Maps Foundation", "Restaurant listings and websites come from Overture Maps Foundation places data (overturemaps.org), release 2026-09-23.1, filtered and reformatted for this app.\n• Data from Meta, Microsoft, DAC and BrightQuery. Available under CDLA Permissive 2.0.\n• Data from Foursquare. Copyright 2024 Foursquare Labs, Inc. All rights reserved. Available under Apache 2.0. Foursquare data was transformed to the Overture schema; this app further filtered and reformatted it. See the NOTICE below.\n• Data from AllThePlaces. Available under CC0 1.0.", "https://overturemaps.org")
                source("Colorado Information Marketplace", "Liquor Licenses in Colorado (Colorado Department of Revenue, Liquor Enforcement Division) and Restaurant Inspections in Boulder County (Boulder County Public Health), from data.colorado.gov, public domain, modified for use in this app. The State of Colorado and Boulder County make no warranty as to the data's accuracy, completeness or timeliness and do not endorse this app.", "https://data.colorado.gov")
                source("City and County of Denver", "Active Business Licenses (Denver Open Data), modified for use in this app. The City and County of Denver is not responsible and shall not be liable to any user or recipient for damages of any kind arising out of the use of data or information provided by the City and County of Denver; the data is provided as is, without warranty of any kind.", "https://opendata-geospatialdenver.hub.arcgis.com")
                source("Honors", "The MICHELIN Guide Colorado 2026 selection and James Beard Foundation awards, finalists, semifinalists and America's Classics are reported as facts and checked by hand against the official announcements. MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Other names belong to their owners.", "https://guide.michelin.com/us/en/colorado")
                source("Maps", "Maps, place cards and directions by Apple Maps.", nil)
            }
            Section("Licenses") {
                NavigationLink("Community Data License Agreement – Permissive 2.0") { LicenseText(file: "CDLA-Permissive-2.0", title: "CDLA Permissive 2.0") }
                NavigationLink("Apache License 2.0") { LicenseText(file: "Apache-2.0", title: "Apache License 2.0") }
                NavigationLink("Foursquare OS Places NOTICE") { LicenseText(file: "Foursquare-NOTICE", title: "Foursquare NOTICE") }
            }
            Section("Privacy") {
                Text("The app collects nothing. Your location, if you allow it, only sorts lists by distance and shows where you are on the map, on this device. Saved places stay on this device.")
                    .font(.subheadline).foregroundStyle(Theme.ink2)
                Link("Privacy policy", destination: Links.privacy)
                Link("Terms of use", destination: Links.terms)
            }
            Section("Help") {
                Link("Report a missing or closed place", destination: Links.correctionEmail)
                Link("Email \(Links.supportEmail)", destination: URL(string: "mailto:\(Links.supportEmail)")!)
                Link("Website", destination: Links.site)
                Text("Data as of \(model.generated). Places open and close; check before you go. Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0")")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
        }
        .navigationTitle("About")
        .tint(Theme.green)
    }

    private func rate(_ group: String) -> String {
        let v = ["Denver", "Boulder County"].compactMap { model.calibration[$0]?.groups[group]?.official }
        guard let lo = v.min(), let hi = v.max() else { return "most" }
        let a = Int((lo * 100).rounded()), b = Int((hi * 100).rounded())
        return a == b ? "\(a)%" : "\(a)–\(b)%"
    }

    @ViewBuilder
    private func source(_ name: String, _ detail: String, _ url: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let url, let u = URL(string: url) { Link(name, destination: u).font(.subheadline.weight(.semibold)) }
            else { Text(name).font(.subheadline.weight(.semibold)) }
            Text(detail).font(.caption).foregroundStyle(Theme.muted)
        }
    }
}

/// A bundled license text (Resources/Licenses), reflowed rather than shown as raw 80-column lines.
struct LicenseText: View {
    let file: String
    let title: String

    var body: some View {
        ScrollView {
            Text(text).font(.footnote).foregroundStyle(Theme.ink).textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding()
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var text: String {
        guard let url = Bundle.main.url(forResource: file, withExtension: "txt"),
              let raw = try? String(contentsOf: url, encoding: .utf8) else { return "License text missing." }
        // join hard-wrapped lines into paragraphs; keep blank lines and list items as breaks
        var out: [String] = []
        for para in raw.components(separatedBy: "\n\n") {
            let lines = para.components(separatedBy: "\n").map { $0.trimmingCharacters(in: .whitespaces) }
            var joined = ""
            for l in lines where !l.isEmpty {
                let startsItem = l.hasPrefix("–") || l.hasPrefix("-") || l.range(of: #"^\(?[a-z0-9]{1,3}[.)]\s"#, options: .regularExpression) != nil
                joined += joined.isEmpty ? l : (startsItem ? "\n" + l : " " + l)
            }
            if !joined.isEmpty { out.append(joined) }
        }
        return out.joined(separator: "\n\n")
    }
}
