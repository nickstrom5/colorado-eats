// Three app-icon concepts for Nick to choose from, each drawn in code and shown at 512, 180 and 60 px.
// A: green chile pepper · B: smothered breakfast burrito · C: Palisade peach. Flag blue ground, a Front Range ridge as the accent.
// Usage: swift scripts/icon-concepts.swift   (run from co-eats/) -> playbook/brand/concepts.png and concept-<x>-1024.png
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let blue = rgb(0x002868), blue2 = rgb(0x173A80), gold = rgb(0xFFD700), white = rgb(0xFFFFFF), ink = rgb(0x0F1B33)

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

/// A: a long green chile, stem at the upper left, curving down to its tip at the lower right.
func chile(_ c: CGContext, _ s: CGFloat) {
    let pod = CGMutablePath()
    pod.move(to: P(s, 0.27, 0.72))
    pod.addCurve(to: P(s, 0.86, 0.27), control1: P(s, 0.60, 0.82), control2: P(s, 0.84, 0.58))
    pod.addCurve(to: P(s, 0.70, 0.30), control1: P(s, 0.83, 0.25), control2: P(s, 0.76, 0.26))
    pod.addCurve(to: P(s, 0.20, 0.53), control1: P(s, 0.58, 0.36), control2: P(s, 0.38, 0.44))
    pod.addCurve(to: P(s, 0.27, 0.72), control1: P(s, 0.13, 0.57), control2: P(s, 0.16, 0.70))
    pod.closeSubpath()
    c.saveGState(); c.addPath(pod); c.clip()
    let grad = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!, colors: [rgb(0x7CC24E), rgb(0x4C9A35), rgb(0x2E6E25)] as CFArray, locations: [0, 0.5, 1])!
    c.drawLinearGradient(grad, start: P(s, 0.45, 0.75), end: P(s, 0.55, 0.35), options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
    // a soft highlight along the top of the pod
    let hi = CGMutablePath()
    hi.move(to: P(s, 0.30, 0.67)); hi.addCurve(to: P(s, 0.76, 0.40), control1: P(s, 0.54, 0.74), control2: P(s, 0.71, 0.55))
    c.setStrokeColor(rgb(0xC8EFA0, 0.75)); c.setLineWidth(s * 0.028); c.setLineCap(.round); c.addPath(hi); c.strokePath()
    c.restoreGState()
    // calyx and stem
    let cap = CGMutablePath()
    cap.move(to: P(s, 0.19, 0.66)); cap.addCurve(to: P(s, 0.33, 0.72), control1: P(s, 0.22, 0.75), control2: P(s, 0.29, 0.76))
    cap.addCurve(to: P(s, 0.19, 0.66), control1: P(s, 0.28, 0.65), control2: P(s, 0.23, 0.62))
    c.setFillColor(rgb(0x3D6B1F)); c.addPath(cap); c.fillPath()
    let stem = CGMutablePath()
    stem.move(to: P(s, 0.25, 0.72)); stem.addCurve(to: P(s, 0.25, 0.86), control1: P(s, 0.22, 0.78), control2: P(s, 0.21, 0.83))
    stem.addCurve(to: P(s, 0.33, 0.88), control1: P(s, 0.28, 0.89), control2: P(s, 0.31, 0.89))
    c.setStrokeColor(rgb(0x5A8A2A)); c.setLineWidth(s * 0.045); c.setLineCap(.round); c.addPath(stem); c.strokePath()
}

/// B: a breakfast burrito lying on a white plate, smothered in green chile down the middle.
func burrito(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(white); c.fillEllipse(in: CGRect(x: s * 0.09, y: s * 0.26, width: s * 0.82, height: s * 0.40))
    c.setFillColor(rgb(0xDCE3EE)); c.fillEllipse(in: CGRect(x: s * 0.15, y: s * 0.30, width: s * 0.70, height: s * 0.32))
    // tortilla roll
    let body = CGPath(roundedRect: CGRect(x: s * 0.16, y: s * 0.38, width: s * 0.68, height: s * 0.26), cornerWidth: s * 0.13, cornerHeight: s * 0.13, transform: nil)
    c.setFillColor(rgb(0xF0CF92)); c.addPath(body); c.fillPath()
    c.setFillColor(rgb(0xD9A85E)); c.fillEllipse(in: CGRect(x: s * 0.17, y: s * 0.42, width: s * 0.06, height: s * 0.05))
    c.fillEllipse(in: CGRect(x: s * 0.75, y: s * 0.53, width: s * 0.05, height: s * 0.04))
    // green chile sauce over the middle, with drips
    let sauce = CGMutablePath()
    sauce.move(to: P(s, 0.30, 0.66))
    sauce.addCurve(to: P(s, 0.72, 0.66), control1: P(s, 0.42, 0.72), control2: P(s, 0.60, 0.72))
    sauce.addCurve(to: P(s, 0.70, 0.40), control1: P(s, 0.78, 0.58), control2: P(s, 0.74, 0.46))
    sauce.addCurve(to: P(s, 0.62, 0.36), control1: P(s, 0.68, 0.33), control2: P(s, 0.64, 0.33))
    sauce.addCurve(to: P(s, 0.52, 0.40), control1: P(s, 0.60, 0.40), control2: P(s, 0.56, 0.42))
    sauce.addCurve(to: P(s, 0.42, 0.35), control1: P(s, 0.48, 0.37), control2: P(s, 0.45, 0.31))
    sauce.addCurve(to: P(s, 0.32, 0.42), control1: P(s, 0.39, 0.39), control2: P(s, 0.34, 0.37))
    sauce.addCurve(to: P(s, 0.30, 0.66), control1: P(s, 0.27, 0.50), control2: P(s, 0.26, 0.60))
    sauce.closeSubpath()
    c.setFillColor(rgb(0x5E9E32)); c.addPath(sauce); c.fillPath()
    // flecks of roasted chile
    c.setFillColor(rgb(0x2F6A1E))
    for (x, y, r) in [(0.40, 0.58, 0.022), (0.55, 0.62, 0.018), (0.62, 0.52, 0.02), (0.47, 0.48, 0.016), (0.36, 0.48, 0.014)] as [(CGFloat, CGFloat, CGFloat)] {
        c.fillEllipse(in: CGRect(x: s * (x - r), y: s * (y - r), width: s * r * 2, height: s * r * 2))
    }
}

/// C: a Palisade peach with its blush, crease, stem and one leaf.
func peach(_ c: CGContext, _ s: CGFloat) {
    let body = CGMutablePath()
    body.addEllipse(in: CGRect(x: s * 0.22, y: s * 0.24, width: s * 0.56, height: s * 0.54))
    c.saveGState(); c.addPath(body); c.clip()
    let grad = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!, colors: [rgb(0xFFD27A), rgb(0xFF9D52), rgb(0xE8503F)] as CFArray, locations: [0, 0.45, 1])!
    c.drawRadialGradient(grad, startCenter: P(s, 0.36, 0.62), startRadius: 0, endCenter: P(s, 0.56, 0.42), endRadius: s * 0.42, options: [.drawsAfterEndLocation])
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

let concepts: [(String, String, (CGContext, CGFloat) -> Void)] = [("a", "A · Green chile", chile), ("b", "B · Smothered burrito", burrito), ("c", "C · Palisade peach", peach)]
func icon(_ size: Int, _ f: (CGContext, CGFloat) -> Void) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); ground(c, s); f(c, s) }
}
// the contact sheet: each concept at 512, 180 and 60 px, the small ones drawn at their real pixel size
let sheet = canvas(1060, 3 * 600 + 40) { c in
    c.setFillColor(white); c.fill(CGRect(x: 0, y: 0, width: 1060, height: 3 * 600 + 40))
    for (i, (_, label, f)) in concepts.enumerated() {
        let y0 = CGFloat(3 * 600 + 40 - (i + 1) * 600)
        let mask = CGPath(roundedRect: CGRect(x: 0, y: 0, width: 1, height: 1), cornerWidth: 0.225, cornerHeight: 0.225, transform: nil)
        for (sz, x) in [(512, 40), (180, 600), (60, 840)] {
            let img = icon(sz, f)
            c.saveGState()
            var t = CGAffineTransform(scaleX: CGFloat(sz), y: CGFloat(sz)).translatedBy(x: CGFloat(x) / CGFloat(sz), y: (y0 + 40) / CGFloat(sz))
            c.addPath(mask.copy(using: &t)!); c.clip()
            c.draw(img, in: CGRect(x: CGFloat(x), y: y0 + 40, width: CGFloat(sz), height: CGFloat(sz)))
            c.restoreGState()
        }
        let attr = NSAttributedString(string: label, attributes: [.font: NSFont.systemFont(ofSize: 30, weight: .bold), .foregroundColor: NSColor(cgColor: ink)!])
        c.textPosition = CGPoint(x: 600, y: y0 + 470); CTLineDraw(CTLineCreateWithAttributedString(attr), c)
        let sub = NSAttributedString(string: "512 · 180 · 60 px", attributes: [.font: NSFont.systemFont(ofSize: 22, weight: .regular), .foregroundColor: NSColor(cgColor: ink)!])
        c.textPosition = CGPoint(x: 600, y: y0 + 432); CTLineDraw(CTLineCreateWithAttributedString(sub), c)
    }
}
save(sheet, "playbook/brand/concepts.png")
for (k, _, f) in concepts { save(icon(1024, f), "playbook/brand/concept-\(k)-1024.png") }
