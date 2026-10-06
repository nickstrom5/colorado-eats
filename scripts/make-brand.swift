// Regenerates the brand images: the app icon (a flat Pueblo green chile on flag blue with a Front Range ridge, Nick's pick 2026-10-06,
// concept A of scripts/icon-concepts-2.swift; it replaced the Palisade peach, which was not local enough), playbook/brand/, and the site's og.png, favicons and manifest icons.
// Usage: swift scripts/make-brand.swift   (run from co-eats/)
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let blue = rgb(0x002868), blue2 = rgb(0x173A80), gold = rgb(0xFFD700), white = rgb(0xFFFFFF), red = rgb(0xBF0A30)

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

/// The ground: flag blue with a low, lighter-blue Front Range ridge along the bottom.
func ground(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(blue); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    let r = CGMutablePath()
    let pts: [(CGFloat, CGFloat)] = [(0, 0.15), (0.10, 0.19), (0.19, 0.16), (0.30, 0.25), (0.38, 0.20), (0.47, 0.28), (0.56, 0.21),
                                     (0.66, 0.26), (0.75, 0.18), (0.86, 0.23), (1, 0.17)]
    r.move(to: P(s, 0, 0)); for (x, y) in pts { r.addLine(to: P(s, x, y)) }; r.addLine(to: P(s, 1, 0)); r.closeSubpath()
    c.setFillColor(blue2); c.addPath(r); c.fillPath()
    // snow caps on the two tallest peaks
    c.setFillColor(rgb(0xFFFFFF, 0.85))
    for (x, y) in [(0.47, 0.28), (0.30, 0.25)] {
        let cap = CGMutablePath()
        cap.move(to: P(s, x, y)); cap.addLine(to: P(s, x - 0.035, y - 0.035)); cap.addLine(to: P(s, x - 0.012, y - 0.026))
        cap.addLine(to: P(s, x + 0.004, y - 0.036)); cap.addLine(to: P(s, x + 0.03, y - 0.03)); cap.closeSubpath()
        c.addPath(cap); c.fillPath()
    }
}

/// A: a Pueblo green chile, flat: one green with a darker underside, a lighter flat highlight, calyx and curled stem.
func chile(_ c: CGContext, _ s: CGFloat) {
    let pod = CGMutablePath()
    pod.move(to: P(s, 0.27, 0.72))
    pod.addCurve(to: P(s, 0.86, 0.27), control1: P(s, 0.60, 0.82), control2: P(s, 0.84, 0.58))
    pod.addCurve(to: P(s, 0.70, 0.30), control1: P(s, 0.83, 0.25), control2: P(s, 0.76, 0.26))
    pod.addCurve(to: P(s, 0.20, 0.53), control1: P(s, 0.58, 0.36), control2: P(s, 0.38, 0.44))
    pod.addCurve(to: P(s, 0.27, 0.72), control1: P(s, 0.13, 0.57), control2: P(s, 0.16, 0.70))
    pod.closeSubpath()
    c.saveGState(); c.addPath(pod); c.clip()
    c.setFillColor(rgb(0x4E9A2E)); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    // the darker underside: a flat band along the bottom edge
    let under = CGMutablePath()
    under.move(to: P(s, 0.14, 0.58)); under.addCurve(to: P(s, 0.88, 0.29), control1: P(s, 0.40, 0.49), control2: P(s, 0.66, 0.40))
    under.addLine(to: P(s, 0.88, 0.0)); under.addLine(to: P(s, 0.0, 0.0)); under.closeSubpath()
    c.setFillColor(rgb(0x3A7A21)); c.addPath(under); c.fillPath()
    // one flat lighter stripe along the top
    let hi = CGMutablePath()
    hi.move(to: P(s, 0.31, 0.665)); hi.addCurve(to: P(s, 0.74, 0.43), control1: P(s, 0.53, 0.72), control2: P(s, 0.69, 0.55))
    c.setStrokeColor(rgb(0x7CC04F)); c.setLineWidth(s * 0.03); c.setLineCap(.round); c.addPath(hi); c.strokePath()
    c.restoreGState()
    let cap = CGMutablePath()
    cap.move(to: P(s, 0.18, 0.66)); cap.addCurve(to: P(s, 0.34, 0.73), control1: P(s, 0.21, 0.76), control2: P(s, 0.29, 0.77))
    cap.addCurve(to: P(s, 0.18, 0.66), control1: P(s, 0.29, 0.65), control2: P(s, 0.22, 0.61))
    c.setFillColor(rgb(0x2F5E1A)); c.addPath(cap); c.fillPath()
    let stem = CGMutablePath()
    stem.move(to: P(s, 0.25, 0.72)); stem.addCurve(to: P(s, 0.25, 0.86), control1: P(s, 0.22, 0.78), control2: P(s, 0.21, 0.83))
    stem.addCurve(to: P(s, 0.33, 0.88), control1: P(s, 0.28, 0.89), control2: P(s, 0.31, 0.89))
    c.setStrokeColor(rgb(0x5A8A2A)); c.setLineWidth(s * 0.045); c.setLineCap(.round); c.addPath(stem); c.strokePath()
}

func icon(_ size: Int) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); ground(c, s); chile(c, s) }
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
