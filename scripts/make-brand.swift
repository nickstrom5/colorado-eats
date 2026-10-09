// Regenerates the brand images: the app icon (a flat Pueblo green chile lying level on flag blue: Nick's pick 2026-10-06, it replaced the
// Palisade peach, which was not local enough; redrawn 2026-10-09 in the shared Eats Ranked icon style Nick approved, same food and colours,
// no ridge, snow, shine or tilt, see ../state-prompts/ICON-STYLE.md), playbook/brand/, and the site's og.png, favicons and manifest icons.
// Usage: swift scripts/make-brand.swift   (run from co-eats/)
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let blue = rgb(0x002868), gold = rgb(0xFFD700), white = rgb(0xFFFFFF), red = rgb(0xBF0A30)

func canvas(_ w: Int, _ h: Int, _ draw: (CGContext) -> Void) -> CGImage {
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true); ctx.interpolationQuality = .high
    draw(ctx)
    return ctx.makeImage()!
}
func save(_ img: CGImage, _ path: String) {
    let url = URL(fileURLWithPath: root + "/" + path)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try! NSBitmapImageRep(cgImage: img).representation(using: .png, properties: [:])!.write(to: url)
    print("wrote", path)
}
func P(_ s: CGFloat, _ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }

/// A Pueblo green chile in side elevation, lying level. Broad, rounded shoulders at the left: the pod is widest there (0.40)
/// and the top edge leaves the shoulder level, then runs down to the tip in one long, nearly straight sweep. The pod is a
/// crescent: the bottom has a round belly under the shoulder, arches up through the middle and comes back down into the tip,
/// so both edges bend the same way and the tip hooks down-right (its centre 0.075 below the shoulder's centre line; a curve
/// in the pod, not a rotation). The tip is blunt, a 47 px round. One green in two flat tones: the base, and a darker underside
/// over the lower 35% of the thickness whose hard edge runs parallel to the bottom contour (light from above, like Wisconsin's
/// top face). A dark calyx sits on the crown like a cap, standing proud of the top edge, with two rounded sepals; the pod's own
/// rounded end shows below it, so the silhouette stays whole in grayscale. A 46 px stem rises from the cap and curls right.
/// No outline, no gloss, no marks. Paints nothing behind the food, so og.png can call it at another size (`chile(c, 400)`).
func chile(_ c: CGContext, _ s: CGFloat) {
    let ox: CGFloat = -0.031, oy: CGFloat = -0.046   // placement: box centred, mass a little low, as on the references
    func pt(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: (x + ox) * s, y: (y + oy) * s) }
    c.setLineCap(.round); c.setLineJoin(.round)

    // pod, 5 segments: top edge from the shoulder (level there) to the tip, the round tip (radius 0.046, from 45° clockwise
    // round to -102°), the bottom edge back to the shoulder (hook, arch, belly), and the rounded stem end in two quarters
    let pod = CGMutablePath()
    pod.move(to: pt(0.290, 0.700))
    pod.addCurve(to: pt(0.883, 0.458), control1: pt(0.460, 0.700), control2: pt(0.656, 0.684))
    pod.addArc(center: pt(0.850, 0.425), radius: 0.046 * s, startAngle: .pi / 4, endAngle: -102 * .pi / 180, clockwise: true)
    pod.addCurve(to: pt(0.290, 0.300), control1: pt(0.625, 0.426), control2: pt(0.590, 0.300))
    pod.addCurve(to: pt(0.165, 0.500), control1: pt(0.210, 0.300), control2: pt(0.165, 0.372))
    pod.addCurve(to: pt(0.290, 0.700), control1: pt(0.165, 0.628), control2: pt(0.210, 0.700))
    pod.closeSubpath()
    c.saveGState(); c.addPath(pod); c.clip()
    c.setFillColor(rgb(0x4E9A2E)); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    // underside: everything below an edge 35% of the way from the bottom contour to the top contour (level under the
    // shoulder, then parallel to the bottom's arch and hook, leaving through the tip); the clip keeps it inside the pod
    let under = CGMutablePath()
    under.move(to: pt(0.020, 0.440)); under.addLine(to: pt(0.290, 0.440))
    under.addCurve(to: pt(0.855, 0.407), control1: pt(0.545, 0.440), control2: pt(0.636, 0.516))
    under.addLine(to: pt(1.034, 0.318)); under.addLine(to: pt(0.980, 0.050)); under.addLine(to: pt(0.020, 0.050))
    under.closeSubpath()
    c.setFillColor(rgb(0x3A7A21)); c.addPath(under); c.fillPath()
    c.restoreGState()

    // stem: a 46 px round-cap stroke rising out of the cap's crown, leaning left, then curling right (root hidden by the cap)
    let stem = CGMutablePath()
    stem.move(to: pt(0.234, 0.700))
    stem.addCurve(to: pt(0.214, 0.795), control1: pt(0.222, 0.735), control2: pt(0.199, 0.755))
    stem.addCurve(to: pt(0.309, 0.815), control1: pt(0.229, 0.830), control2: pt(0.284, 0.840))
    c.setStrokeColor(rgb(0x5A8A2A)); c.setLineWidth(s * 0.045); c.addPath(stem); c.strokePath()

    // calyx: a cap on the crown, 0.14 wide, domed about 0.03 above the top edge and flush with the rounded end, its lower
    // edge two rounded sepals hanging onto the shoulder
    let cap = CGMutablePath()
    cap.move(to: pt(0.310, 0.696))
    cap.addCurve(to: pt(0.168, 0.590), control1: pt(0.260, 0.756), control2: pt(0.168, 0.725))
    cap.addCurve(to: pt(0.242, 0.640), control1: pt(0.179, 0.545), control2: pt(0.222, 0.560))
    cap.addCurve(to: pt(0.310, 0.696), control1: pt(0.262, 0.570), control2: pt(0.305, 0.655))
    cap.closeSubpath()
    c.setFillColor(rgb(0x2F5E1A)); c.addPath(cap); c.fillPath()
}

func icon(_ size: Int) -> CGImage {
    // flag blue edge to edge, then the chile: no ridge, snow, gloss or tilt
    canvas(size, size) { c in let s = CGFloat(size); c.setFillColor(blue); c.fill(CGRect(x: 0, y: 0, width: s, height: s)); chile(c, s) }
}

func text(_ c: CGContext, _ str: String, font: NSFont, color: CGColor, at p: CGPoint) {
    let attr = NSAttributedString(string: str, attributes: [.font: font, .foregroundColor: NSColor(cgColor: color)!])
    c.textPosition = p
    CTLineDraw(CTLineCreateWithAttributedString(attr), c)
}
func heavy(_ size: CGFloat) -> NSFont {
    NSFont(name: "HelveticaNeue-CondensedBlack", size: size) ?? NSFont.systemFont(ofSize: size, weight: .black)
}

let appIcon = icon(1024)
save(appIcon, "ColoradoEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png")
save(appIcon, "playbook/brand/icon-1024.png")
save(icon(512), "docs/icon-512.png")
save(icon(192), "docs/icon-192.png")
save(icon(180), "docs/apple-touch-icon.png")
save(icon(32), "docs/favicon-32.png")

let count = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "16,000+"
let og = canvas(1200, 630) { c in
    c.setFillColor(blue); c.fill(CGRect(x: 0, y: 0, width: 1200, height: 630))
    c.setFillColor(gold); c.fill(CGRect(x: 72, y: 470, width: 90, height: 12))
    text(c, "COLORADO", font: heavy(128), color: white, at: CGPoint(x: 66, y: 322))
    text(c, "EATS", font: heavy(128), color: gold, at: CGPoint(x: 66, y: 204))
    text(c, "Green chile & brewpub guide · \(count) Colorado restaurants", font: NSFont.systemFont(ofSize: 32, weight: .semibold), color: white, at: CGPoint(x: 70, y: 150))
    text(c, "Free for iPhone and iPad", font: NSFont.systemFont(ofSize: 30, weight: .regular), color: gold, at: CGPoint(x: 70, y: 96))
    c.saveGState(); c.translateBy(x: 770, y: 150); chile(c, 400); c.restoreGState()
    c.setFillColor(red); c.fill(CGRect(x: 0, y: 0, width: 1200, height: 10))
}
save(og, "docs/og.png")
