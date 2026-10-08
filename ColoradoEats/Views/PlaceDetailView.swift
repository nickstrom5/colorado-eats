import SwiftUI
import MapKit

struct PlaceDetailView: View {
    @Environment(AppModel.self) private var model
    @Environment(LocationService.self) private var location
    let place: Place

    @State private var mapItem: MKMapItem?
    @State private var lookingUp = false
    @State private var notOnAppleMaps = false
    @State private var appleMapsFailed = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                actions
                if let c = place.coordinate { mapSnippet(c) }
                if place.handChecked && (place.note != nil || place.dishes != nil || place.founded != nil || place.seasonal != nil) { checked }
                if place.hasHonors { honors }
                if let i = place.inspection { inspections(i) }
                records
                listing
            }
            .padding(16)
        }
        .background(Theme.surface)
        .inlineTitle(place.name)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { model.toggleSaved(place) } label: {
                    Label(model.isSaved(place) ? "Saved" : "Save", systemImage: model.isSaved(place) ? "heart.fill" : "heart")
                }
                ShareLink(item: shareText) { Label("Share", systemImage: "square.and.arrow.up") }
            }
        }
        .mapItemDetailSheet(item: $mapItem)
        .alert("Not on Apple Maps", isPresented: $notOnAppleMaps) {
            Button("Open Apple Maps anyway") { AppleMaps.openInMaps(place) }
            Button("OK", role: .cancel) {}
        } message: {
            Text("Apple Maps doesn't have a listing for \(place.name) at this spot, so there are no ratings or hours to show here.")
        }
        .alert("Couldn't reach Apple Maps", isPresented: $appleMapsFailed) {
            Button("Try again") { lookUp() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Check your connection and try again.")
        }
    }

    /// Apple's place card for this place; "not on Apple Maps" only when Apple answered and had no listing here.
    private func lookUp() {
        lookingUp = true
        Task {
            let result = await AppleMaps.findItem(for: place)
            lookingUp = false
            switch result {
            case .found(let item): mapItem = item
            case .notListed: notOnAppleMaps = true
            case .failed: appleMapsFailed = true
            }
        }
    }

    // MARK: sections

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            // "DENVER" alone (Denver is a city and county); "PUEBLO · PUEBLO COUNTY" elsewhere
            Text((place.city ?? "Colorado").uppercased() + (place.county.flatMap { $0 == place.city ? nil : " · " + $0.uppercased() } ?? ""))
                .font(.caption.weight(.bold)).tracking(1.2).foregroundStyle(Theme.green2)
            Text(place.name.uppercased())
                .displayFont(38).foregroundStyle(Theme.green)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text([place.fullAddress, place.cuisine].filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.subheadline).foregroundStyle(Theme.ink2)
                .textSelection(.enabled)
            if let here = model.screenshotLocation ?? location.location, let l = place.location {
                Text("\(here.milesText(to: l)) away").font(.subheadline).foregroundStyle(Theme.muted)
            }
            PlaceChips(place: place)
        }
    }

    private var actions: some View {
        VStack(spacing: 10) {
            Button { lookUp() } label: {
                HStack {
                    if lookingUp { ProgressView().tint(Theme.green) } else { Image(systemName: "star.bubble") }
                    Text("Ratings, hours & photos").fontWeight(.semibold)
                    Spacer()
                    Text("Apple Maps").font(.caption).foregroundStyle(Theme.green2)
                }
                .padding(14)
                .foregroundStyle(Theme.green)
                .background(RoundedRectangle(cornerRadius: 12).fill(Theme.gold))
            }
            .disabled(place.coordinate == nil || lookingUp)
            .accessibilityHint("Opens the Apple Maps place card with current ratings and hours")

            HStack(spacing: 10) {
                actionButton("Directions", "arrow.triangle.turn.up.right.diamond") { AppleMaps.openInMaps(place, directions: true) }
                if let phone = place.phone, let url = URL(string: "tel:\(phone.filter { $0.isNumber || $0 == "+" })") {
                    actionButton("Call", "phone") { UIApplication.shared.open(url) }
                }
                if let web = place.website {
                    actionButton("Website", "safari") { UIApplication.shared.open(web) }
                }
            }
        }
    }

    private func actionButton(_ title: String, _ icon: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon).font(.title3)
                Text(title).font(.caption.weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 56)
            .foregroundStyle(Theme.green)
            .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.rule2))
        }
    }

    private func mapSnippet(_ c: CLLocationCoordinate2D) -> some View {
        Map(initialPosition: .region(MKCoordinateRegion(center: c, latitudinalMeters: 900, longitudinalMeters: 900)), interactionModes: []) {
            Marker(place.name, systemImage: place.tags.contains(.greenChile) ? "flame.fill" : place.tags.contains(.brewpub) ? "mug.fill" : "fork.knife", coordinate: c).tint(Theme.green)
        }
        .frame(height: 170)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .onTapGesture { AppleMaps.openInMaps(place) }
        .accessibilityLabel("Map of \(place.name). Opens Apple Maps.")
        .accessibilityAddTraits(.isButton)
    }

    private var checked: some View {
        section("Hand-checked") {
            VStack(alignment: .leading, spacing: 8) {
                if let note = place.note { Text(note).font(.subheadline).foregroundStyle(Theme.ink2) }
                if let d = place.dishes { fact("On the menu", d.components(separatedBy: "; ").joined(separator: ", ")) }
                if let f = place.founded {
                    fact("Open here since", "\(f)")
                    // the note explains the year; without a year it only repeated the description above
                    if let fn = place.foundedNote { Text(fn).font(.caption).foregroundStyle(Theme.ink2) }
                }
                if let sea = place.seasonal { fact("Season", sea) }
                Text("Checked by hand against a 2025 or 2026 source: the place's own site or menu, or local news. Menus and seasons change, and mountain places close for mud season in spring and fall, so check before you go.")
                    .font(.caption).foregroundStyle(Theme.ink2)
            }
        }
    }

    private var honors: some View {
        section("Honors") {
            VStack(alignment: .leading, spacing: 8) {
                if let m = place.michelin.label {
                    Label(m + " · MICHELIN Guide Colorado 2026", systemImage: "rosette").font(.subheadline).foregroundStyle(Theme.ink)
                }
                ForEach(lines(place.jamesBeard, prefix: "James Beard: "), id: \.self) { l in
                    Label(l, systemImage: "rosette").font(.subheadline).foregroundStyle(Theme.ink)
                }
                Text("Honors are facts, not ratings. MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation.")
                    .font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private func inspections(_ i: InspectionRecord) -> some View {
        section("Health inspections · Boulder County") {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .center, spacing: 12) {
                    ResultBadge(result: i.r, large: true)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(DayFormat.text(i.d).map { "Latest inspection \($0)" } ?? "Latest inspection: date not published").font(.headline).foregroundStyle(Theme.ink)
                        Text("\(i.p) risk point\(i.p == 1 ? "" : "s") · official result, as recorded").font(.caption).foregroundStyle(Theme.muted)
                    }
                }
                if i.d == nil || i.h.contains(where: { $0.d == nil }) {
                    Text("Inspection date not published: recorded during Boulder County's September 2025 system move.")
                        .font(.caption).foregroundStyle(Theme.ink2)
                }
                // by position: a routine inspection and its same-day re-inspection are two entries, and undated ones can look alike
                ForEach(Array(i.h.enumerated()), id: \.offset) { _, v in
                    HStack(alignment: .firstTextBaseline) {
                        Text(DayFormat.text(v.d) ?? "Date not published").font(.subheadline).monospacedDigit().foregroundStyle(Theme.ink2)
                        Text(v.t).font(.subheadline).foregroundStyle(Theme.muted)
                        Spacer(minLength: 8)
                        Text("\(v.r.label) · \(v.p) pts").font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.trailing)
                    }
                }
                if let items = i.i, !items.isEmpty {
                    fact("Cited at the latest inspection", items.prefix(8).joined(separator: "; ") + (items.count > 8 ? "…" : ""))
                }
                Text("Colorado rates retail food inspections Pass (0–49 risk points), Re-Inspection Required (50–109) or Closure (110+ points). Boulder County also records a Closure when it closes a place for an imminent health hazard, such as a sewage backup, whatever the points. Fewer points is better. Source: Boulder County Public Health on data.colorado.gov, inspections through \(DayFormat.text(model.inspectionsThrough) ?? model.inspectionsThrough), published \(DayFormat.text(model.inspectionsPublished) ?? model.inspectionsPublished). One inspection is a snapshot of one day.")
                    .font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private var records: some View {
        section("Official records") {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(place.licenses, id: \.self) { l in
                    kv(l.src, [l.type, Self.unbroken(l.id), expires(l)].compactMap { $0 }.joined(separator: " · "))
                }
                kv("Serves alcohol", place.servesAlcohol)
                Text(recordsNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private var listing: some View {
        section("How we know it's here") {
            VStack(alignment: .leading, spacing: 8) {
                kv("Listed as", place.tier.label)
                if place.tier == .licensed { kv("Official record", place.jurisdiction.listName) }
                if place.chainCount >= 2 { kv("Locations in Colorado", place.chainCount.formatted()) }
                Text(listingNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    /// A license on the state's active list stays valid while its renewal is pending, so only a date on or after the list's own
    /// date is shown (the pipeline already leaves the others out; an older data file had them).
    private func expires(_ l: LicenseRecord) -> String? {
        guard let exp = l.exp, exp >= model.liquorUpdated, let text = DayFormat.text(exp) else { return nil }
        return "expires " + text
    }

    /// "2024-BFN-0006294" with non-breaking hyphens, so a license number never wraps in the middle
    private static func unbroken(_ id: String) -> String { id.replacingOccurrences(of: "-", with: "\u{2011}") }

    /// Where the records above come from, naming only the lists this place actually matched.
    private var recordsNote: String {
        let denver = place.licenses.contains { $0.src.hasPrefix("Denver") }
        let state = place.licenses.contains { $0.src.hasPrefix("Colorado") }
        let unknown = "Most Colorado counties don't publish their records in bulk, so a missing record means unknown, not unlicensed."
        if !denver && !state {
            return place.inspection == nil
                ? "No Denver license, state liquor license or Boulder County inspection record matched this place. " + unknown
                : "No Denver license or state liquor license matched this place; its Boulder County inspections are above. " + unknown
        }
        var from: [String] = []
        if denver { from.append("the City and County of Denver's active business licenses" + (DayFormat.text(model.denverUpdated).map { " (as of \($0))" } ?? "")) }
        if state { from.append("the Colorado Department of Revenue's active liquor licenses (as of \(DayFormat.text(model.liquorUpdated) ?? model.liquorUpdated))") }
        return "From " + from.joined(separator: " and ") + "."
    }

    private var listingNote: String {
        let checked = place.handChecked
        if place.source == "research" {
            return "On our hand-checked list (checked against a 2025 or 2026 source). The open map data didn't list it as a place to eat, so it's placed from its own map listing or street address."
        }
        switch place.tier {
        case .licensed:
            return place.source == "official"
                ? "From the \(place.jurisdiction.listName). The open map data didn't have it, so its location comes from the record's street address."
                : "Matched to the \(place.jurisdiction.listName)."
        case .confirmed, .listing:
            let rate = model.matchRate(for: place)
            let base = place.tier == .confirmed
                ? "A high-confidence listing in Overture's open map data."
                : "A single listing in Overture's open map data, so it may be closed or misfiled."
            let measured = rate.map { " Checked against Denver's licenses and Boulder County's inspected facilities, listings like this matched an official record \($0) of the time." } ?? ""
            return base + measured + (checked ? " It's also on our hand-checked list, checked against a 2025 or 2026 source." : "")
        }
    }

    // MARK: helpers

    private var shareText: String {
        [place.name, place.fullAddress, "via Colorado Eats", Links.site.absoluteString].filter { !$0.isEmpty }.joined(separator: "\n")
    }

    private func lines(_ s: String?, prefix: String) -> [String] {
        (s ?? "").components(separatedBy: "; ").filter { !$0.isEmpty }.map { prefix + $0 }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title.uppercased()).font(.caption.weight(.bold)).tracking(1).foregroundStyle(Theme.ink2)
            Divider()
            content()
        }
    }

    private func fact(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
            Text(value).font(.subheadline).foregroundStyle(Theme.ink2)
        }
    }

    @ViewBuilder
    private func kv(_ k: String, _ v: String?) -> some View {
        if let v {
            HStack(alignment: .firstTextBaseline) {
                Text(k).font(.subheadline).foregroundStyle(Theme.ink2)
                Spacer(minLength: 12)
                Text(v).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.trailing)
            }
        }
    }
}

extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
