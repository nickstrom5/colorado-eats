// Second round of icon concepts (2026-10-06): Nick wants something more local to Colorado than the peach, and flat, not glossy.
// A: Pueblo green chile · B: Rocky Mountain rainbow trout · C: smothered burrito. Flag blue ground with a Front Range ridge.
// Usage: swift scripts/icon-concepts-2.swift   (run from co-eats/) -> playbook/brand/concepts-2.png and concept2-<x>-1024.png
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
let blue = rgb(0x002868), blue2 = rgb(0x173A80), white = rgb(0xFFFFFF), ink = rgb(0x0F1B33)

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

/// B: a Rocky Mountain rainbow trout, flat: olive back, pale belly, the pink stripe, black spots, tail, eye.
func trout(_ c: CGContext, _ s: CGFloat) {
    let body = CGMutablePath()   // facing left, nose at x 0.12, tail joint at x 0.74
    body.move(to: P(s, 0.12, 0.53))
    body.addCurve(to: P(s, 0.74, 0.56), control1: P(s, 0.26, 0.72), control2: P(s, 0.58, 0.68))
    body.addLine(to: P(s, 0.74, 0.48))
    body.addCurve(to: P(s, 0.12, 0.53), control1: P(s, 0.58, 0.34), control2: P(s, 0.26, 0.36))
    body.closeSubpath()
    // tail and fins first, so the body sits over them
    let tail = CGMutablePath()
    tail.move(to: P(s, 0.72, 0.52)); tail.addLine(to: P(s, 0.90, 0.66)); tail.addCurve(to: P(s, 0.88, 0.38), control1: P(s, 0.86, 0.56), control2: P(s, 0.86, 0.48))
    tail.closeSubpath()
    c.setFillColor(rgb(0x6E7F3C)); c.addPath(tail); c.fillPath()
    let dorsal = CGMutablePath()
    dorsal.move(to: P(s, 0.40, 0.64)); dorsal.addLine(to: P(s, 0.48, 0.71)); dorsal.addLine(to: P(s, 0.54, 0.64)); dorsal.closeSubpath()
    c.addPath(dorsal); c.fillPath()
    let pelvic = CGMutablePath()
    pelvic.move(to: P(s, 0.42, 0.41)); pelvic.addLine(to: P(s, 0.47, 0.35)); pelvic.addLine(to: P(s, 0.52, 0.41)); pelvic.closeSubpath()
    c.setFillColor(rgb(0xD9B9A0)); c.addPath(pelvic); c.fillPath()
    c.saveGState(); c.addPath(body); c.clip()
    c.setFillColor(rgb(0xE9D8C4)); c.fill(CGRect(x: 0, y: 0, width: s, height: s))              // pale belly
    let back = CGMutablePath()
    back.move(to: P(s, 0.08, 0.55)); back.addCurve(to: P(s, 0.80, 0.53), control1: P(s, 0.30, 0.56), control2: P(s, 0.56, 0.56))
    back.addLine(to: P(s, 0.80, 0.80)); back.addLine(to: P(s, 0.08, 0.80)); back.closeSubpath()
    c.setFillColor(rgb(0x7A8C44)); c.addPath(back); c.fillPath()                                   // olive back
    let stripe = CGMutablePath()
    stripe.move(to: P(s, 0.16, 0.53)); stripe.addCurve(to: P(s, 0.76, 0.52), control1: P(s, 0.34, 0.50), control2: P(s, 0.58, 0.50))
    c.setStrokeColor(rgb(0xE8838A)); c.setLineWidth(s * 0.055); c.setLineCap(.round); c.addPath(stripe); c.strokePath()   // the rainbow stripe
    c.setFillColor(rgb(0x1E2416))
    for (x, y, r) in [(0.30, 0.61, 0.012), (0.38, 0.63, 0.010), (0.47, 0.62, 0.012), (0.55, 0.60, 0.010), (0.63, 0.58, 0.011),
                      (0.42, 0.58, 0.009), (0.58, 0.55, 0.009), (0.68, 0.54, 0.009)] as [(CGFloat, CGFloat, CGFloat)] {
        c.fillEllipse(in: CGRect(x: s * (x - r), y: s * (y - r), width: s * r * 2, height: s * r * 2))
    }
    c.restoreGState()
    c.setFillColor(white); c.fillEllipse(in: CGRect(x: s * 0.175, y: s * 0.545, width: s * 0.04, height: s * 0.04))
    c.setFillColor(rgb(0x1E2416)); c.fillEllipse(in: CGRect(x: s * 0.185, y: s * 0.555, width: s * 0.02, height: s * 0.02))
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

let concepts: [(String, String, (CGContext, CGFloat) -> Void)] = [("a", "A · Pueblo green chile", chile), ("b", "B · Rainbow trout", trout), ("c", "C · Smothered burrito", burrito)]
func icon(_ size: Int, _ f: (CGContext, CGFloat) -> Void) -> CGImage {
    canvas(size, size) { c in let s = CGFloat(size); ground(c, s); f(c, s) }
}
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
save(sheet, "playbook/brand/concepts-2.png")
for (k, _, f) in concepts { save(icon(1024, f), "playbook/brand/concept2-\(k)-1024.png") }
