// Regenerates the brand images: the app icon (a Palisade peach on flag blue with a Front Range ridge, Nick's pick 2026-10-05,
// concept C of scripts/icon-concepts.swift, made flat instead of glossy on 2026-10-06), playbook/brand/, and the site's og.png, favicons and manifest icons.
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

/// C: a Palisade peach with its blush, crease, stem and one leaf.
func peach(_ c: CGContext, _ s: CGFloat) {
    let body = CGMutablePath()
    body.addEllipse(in: CGRect(x: s * 0.22, y: s * 0.24, width: s * 0.56, height: s * 0.54))
    c.saveGState(); c.addPath(body); c.clip()
    // flat, not glossy (Nick, 2026-10-06): one solid peach colour with a single flat blush on the right, no highlight gradient
    c.setFillColor(rgb(0xFFA35A)); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    c.setFillColor(rgb(0xF7864F)); c.fillEllipse(in: CGRect(x: s * 0.50, y: s * 0.20, width: s * 0.40, height: s * 0.40))
    // the crease
    let crease = CGMutablePath()
    crease.move(to: P(s, 0.50, 0.76)); crease.addCurve(to: P(s, 0.44, 0.30), control1: P(s, 0.40, 0.62), control2: P(s, 0.38, 0.42))
    c.setStrokeColor(rgb(0xC9443A, 0.55)); c.setLineWidth(s * 0.02); c.setLineCap(.round); c.addPath(crease); c.strokePath()
    c.restoreGState()
    // stem and leaf
    let stem = CGMutablePath()
    stem.move(to: P(s, 0.50, 0.75)); stem.addCurve(to: P(s, 0.53, 0.84), control1: P(s, 0.51, 0.79), control2: P(s, 0.52, 0.82))
    c.setStrokeColor(rgb(0x6B4A2B)); c.setLineWidth(s * 0.03); c.addPath(stem); c.strokePath()
    let leaf = CGMutablePath()
    leaf.move(to: P(s, 0.52, 0.80)); leaf.addCurve(to: P(s, 0.80, 0.86), control1: P(s, 0.60, 0.92), control2: P(s, 0.74, 0.93))
    leaf.addCurve(to: P(s, 0.52, 0.80), control1: P(s, 0.72, 0.78), control2: P(s, 0.60, 0.75))
    c.setFillColor(rgb(0x4C9A35)); c.addPath(leaf); c.fillPath()
    c.setStrokeColor(rgb(0x2E6E25)); c.setLineWidth(s * 0.008)
    let vein = CGMutablePath(); vein.move(to: P(s, 0.54, 0.80)); vein.addCurve(to: P(s, 0.77, 0.86), control1: P(s, 0.62, 0.84), control2: P(s, 0.70, 0.86))
    c.addPath(vein); c.strokePath()
}

func icon(_ size: Int) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); ground(c, s); peach(c, s) }
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
    c.saveGState(); c.translateBy(x: 780, y: 170); peach(c, 380); c.restoreGState()
    c.setFillColor(red); c.fill(CGRect(x: 0, y: 0, width: 1200, height: 10))
}
save(og, "docs/og.png")
