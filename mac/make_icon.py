"""Draws the app icon (blue squircle + white location arrow) into an .icns. Usage: make_icon.py out.icns"""

import os
import subprocess
import sys
import tempfile

import AppKit


def render(px):
    img = AppKit.NSImage.alloc().initWithSize_((px, px))
    img.lockFocus()
    inset = px * 0.1  # macOS icon grid leaves a margin around the tile
    rect = AppKit.NSMakeRect(inset, inset, px - 2 * inset, px - 2 * inset)
    tile = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, rect.size.width * 0.225, rect.size.width * 0.225)
    top = AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.33, 0.68, 1.0, 1)
    bottom = AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.0, 0.40, 0.95, 1)
    AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(bottom, top).drawInBezierPath_angle_(tile, 90)

    cfg = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_(px * 0.42, AppKit.NSFontWeightSemibold)
    sym = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_("location.fill", None).imageWithSymbolConfiguration_(cfg)
    white = sym.copy()
    white.lockFocus()
    AppKit.NSColor.whiteColor().set()
    AppKit.NSRectFillUsingOperation(AppKit.NSMakeRect(0, 0, *white.size()), AppKit.NSCompositingOperationSourceAtop)
    white.unlockFocus()
    w, h = white.size()
    white.drawInRect_(AppKit.NSMakeRect((px - w) / 2 - px * 0.01, (px - h) / 2 - px * 0.01, w, h))
    img.unlockFocus()
    rep = AppKit.NSBitmapImageRep.alloc().initWithData_(img.TIFFRepresentation())
    return rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})


if __name__ == "__main__":
    out = sys.argv[1]
    with tempfile.TemporaryDirectory() as d:
        iconset = os.path.join(d, "icon.iconset")
        os.mkdir(iconset)
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
                render(size * scale).writeToFile_atomically_(os.path.join(iconset, name), True)
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    print("icon:", out)
