import SwiftUI

/// Colorado flag palette, light only: blue #002868, red #BF0A30, gold #FFD700, white.
/// Gold is always a fill with blue text on it (gold text on white is 1.4:1 and fails contrast). The names `green`/`gold` are kept
/// from Wisconsin Eats so the shared views read the same; here `green` is the flag's blue.
enum Theme {
    static let green = Color(hex: 0x002868)      // flag blue: titles, tint, primary text accents
    static let green2 = Color(hex: 0x1C3F86)
    static let gold = Color(hex: 0xFFD700)       // fills only
    static let goldSoft = Color(hex: 0xFFF1A6)
    static let red = Color(hex: 0xBF0A30)        // MICHELIN chips and Closure results only
    static let ink = Color(hex: 0x0F1B33)
    static let ink2 = Color(hex: 0x2A3A5A)
    static let muted = Color(hex: 0x4E5B73)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xF1F4F9)
    static let surface3 = Color(hex: 0xE0E6F0)
    static let rule = Color(hex: 0xDCE2EC)
    static let rule2 = Color(hex: 0xB5C0D3)
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

/// A small uppercase label: "GREEN CHILE", "1 MICHELIN STAR".
struct Chip: View {
    enum Style { case gold, green, red, plain, dashed }
    let text: String
    var style: Style = .plain

    var body: some View {
        Text(text.uppercased())
            .font(.caption2.weight(.bold))
            .tracking(0.4)
            .padding(.horizontal, 7).padding(.vertical, 3)
            .foregroundStyle(style == .green || style == .red ? Color.white : style == .dashed ? Theme.muted : Theme.green)
            .background {
                RoundedRectangle(cornerRadius: 5).fill(style == .gold ? Theme.goldSoft : style == .green ? Theme.green : style == .red ? Theme.red
                                                       : style == .dashed ? .clear : Theme.surface2)
            }
            .overlay {
                if style == .dashed { RoundedRectangle(cornerRadius: 5).strokeBorder(Theme.rule2, style: StrokeStyle(lineWidth: 1, dash: [3, 2])) }
            }
            .accessibilityLabel(text)
    }
}

/// Colorado's official inspection result, as recorded: Pass, Re-Inspection Required or Closure. Never a grade of ours.
struct ResultBadge: View {
    let result: InspectionResult
    var large = false

    var body: some View {
        Text(result.label.uppercased())
            .font(large ? .footnote.weight(.heavy) : .caption2.weight(.heavy))
            .tracking(0.4)
            .padding(.horizontal, large ? 10 : 7).padding(.vertical, large ? 6 : 3)
            .foregroundStyle(result.ink)
            .background(RoundedRectangle(cornerRadius: 6).fill(result.fill))
            .accessibilityLabel("Official inspection result: \(result.label)")
    }
}

/// The Front Range, drawn once under the Home header: a low ridge with two snow caps.
struct RidgeLine: View {
    var body: some View {
        Canvas { ctx, size in
            let w = size.width, h = size.height
            let pts: [(CGFloat, CGFloat)] = [(0, 0.55), (0.07, 0.40), (0.13, 0.50), (0.22, 0.12), (0.29, 0.38), (0.36, 0.20), (0.44, 0.45),
                                             (0.52, 0.05), (0.60, 0.35), (0.68, 0.22), (0.76, 0.48), (0.85, 0.30), (0.93, 0.50), (1, 0.42)]
            var ridge = Path()
            ridge.move(to: CGPoint(x: 0, y: h))
            for (x, y) in pts { ridge.addLine(to: CGPoint(x: x * w, y: y * h)) }
            ridge.addLine(to: CGPoint(x: w, y: h)); ridge.closeSubpath()
            ctx.fill(ridge, with: .color(Theme.green))
            for (x, y) in [(0.52, 0.05), (0.22, 0.12)] {
                var cap = Path()
                cap.move(to: CGPoint(x: x * w, y: y * h))
                cap.addLine(to: CGPoint(x: x * w - h * 0.32, y: (y + 0.30) * h))
                cap.addLine(to: CGPoint(x: x * w - h * 0.08, y: (y + 0.22) * h))
                cap.addLine(to: CGPoint(x: x * w + h * 0.05, y: (y + 0.31) * h))
                cap.addLine(to: CGPoint(x: x * w + h * 0.30, y: (y + 0.27) * h))
                cap.closeSubpath()
                ctx.fill(cap, with: .color(.white))
            }
            ctx.fill(Path(CGRect(x: 0, y: h - 3, width: w, height: 3)), with: .color(Theme.red))
        }
        .accessibilityHidden(true)
    }
}

/// Condensed, heavy display type for titles and big numbers (the system font's compressed width). It scales with the
/// reader's text size, capped at 1.6× so a big number can't swallow its row.
struct DisplayFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .black
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight).width(.compressed))
    }
}

extension View {
    func displayFont(_ size: CGFloat, weight: Font.Weight = .black) -> some View {
        modifier(DisplayFont(size: size, weight: weight))
    }
}

extension View {
    /// An inline navigation title in the display type. UINavigationBar.appearance() didn't reach every SwiftUI bar on iOS 27
    /// (the Map title went from compressed blue to plain black after a push and pop; place titles were always plain), so the
    /// title is our own view in the bar. The navigation title is still set, for the back button and VoiceOver.
    func inlineTitle(_ title: String) -> some View {
        navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(title).displayFont(19, weight: .heavy).foregroundStyle(Theme.green)
                        .lineLimit(1).minimumScaleFactor(0.7)
                        .accessibilityAddTraits(.isHeader)
                }
            }
    }
}
