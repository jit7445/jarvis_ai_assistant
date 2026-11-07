import math

import AppKit
import objc
import Quartz
from PyObjCTools import AppHelper

from jarvis.core.assistant import State

CARD_W, CARD_H = 340, 66
RADIUS = 16
PAD = 22
BOX = 50
LEFT = 11

_DEFAULT_BODY = {State.LISTENING: "Listening…", State.THINKING: "Thinking…"}

_ICONS = {
    State.IDLE: "mic",
    State.LISTENING: "mic.fill",
    State.THINKING: "waveform",
    State.HEARD: "waveform",
    State.CONFIRMING: "questionmark",
    State.DONE: "checkmark",
    State.FAILED: "exclamationmark",
}

_ACCENT = {
    State.IDLE: (0.30, 0.72, 0.95),
    State.LISTENING: (0.25, 0.82, 1.0),
    State.THINKING: (0.35, 0.62, 1.0),
    State.HEARD: (0.35, 0.62, 1.0),
    State.CONFIRMING: (1.0, 0.74, 0.28),
    State.DONE: (0.30, 0.95, 0.75),
    State.FAILED: (1.0, 0.38, 0.42),
}

# Seconds per turn of the outer ring; the tick ring turns the other way at a slower pace.
_SPIN_SECONDS = {State.IDLE: 16.0, State.LISTENING: 7.0, State.THINKING: 1.6, State.HEARD: 1.6}


def _cg(r: float, g: float, b: float, a: float = 1.0):
    return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, a).CGColor()


def _ns(r: float, g: float, b: float, a: float = 1.0):
    return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, a)


def _symbol(name: str, size: float, weight=AppKit.NSFontWeightSemibold):
    image = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
    config = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_(size, weight)
    return image.imageWithSymbolConfiguration_(config)


def _rounded_mask(radius: float):
    side = 2 * radius + 1

    def draw(rect):
        AppKit.NSColor.blackColor().set()
        AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius).fill()
        return True

    image = AppKit.NSImage.imageWithSize_flipped_drawingHandler_((side, side), False, draw)
    image.setCapInsets_(AppKit.NSEdgeInsets(radius, radius, radius, radius))
    image.setResizingMode_(AppKit.NSImageResizingModeStretch)
    return image


class _ClickTarget(AppKit.NSObject):
    def initWithCallback_(self, callback):
        self = objc.super(_ClickTarget, self).init()
        if self is not None:
            self.callback = callback
        return self

    def clicked_(self, sender) -> None:
        self.callback()


class Overlay:
    """A floating card near the bottom of the screen that never takes focus. Main thread only."""

    def __init__(self, on_close=None) -> None:
        screen = AppKit.NSScreen.mainScreen().visibleFrame()
        width, height = CARD_W + 2 * PAD, CARD_H + 2 * PAD
        x = screen.origin.x + (screen.size.width - width) / 2
        y = screen.origin.y + 14
        self._panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((x, y), (width, height)),
            AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel,
            AppKit.NSBackingStoreBuffered, False)
        p = self._panel
        p.setLevel_(AppKit.NSStatusWindowLevel)
        p.setOpaque_(False)
        p.setBackgroundColor_(AppKit.NSColor.clearColor())
        p.setHasShadow_(False)
        p.setBecomesKeyOnlyIfNeeded_(True)
        p.setHidesOnDeactivate_(False)
        p.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorIgnoresCycle)
        p.setAppearance_(AppKit.NSAppearance.appearanceNamed_(AppKit.NSAppearanceNameDarkAqua))
        p.setMovableByWindowBackground_(True)
        p.setAlphaValue_(0.0)

        root = AppKit.NSView.alloc().initWithFrame_(((0, 0), (width, height)))
        p.setContentView_(root)

        card_rect = ((0, 0), (CARD_W, CARD_H))
        card_path = Quartz.CGPathCreateWithRoundedRect(card_rect, RADIUS, RADIUS, None)
        self._card = AppKit.NSView.alloc().initWithFrame_(((PAD, PAD), (CARD_W, CARD_H)))
        self._card.setWantsLayer_(True)
        glow = self._card.layer()
        glow.setShadowPath_(card_path)
        glow.setShadowColor_(_cg(0.25, 0.82, 1.0))
        glow.setShadowOpacity_(0.45)
        glow.setShadowRadius_(12)
        glow.setShadowOffset_((0, 0))
        root.addSubview_(self._card)

        blur = AppKit.NSVisualEffectView.alloc().initWithFrame_(card_rect)
        blur.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
        blur.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        blur.setState_(AppKit.NSVisualEffectStateActive)
        blur.setMaskImage_(_rounded_mask(RADIUS))
        self._card.addSubview_(blur)

        tint = AppKit.NSView.alloc().initWithFrame_(card_rect)
        tint.setWantsLayer_(True)
        tint.layer().setBackgroundColor_(_cg(0.01, 0.03, 0.08, 0.80))
        tint.layer().setCornerRadius_(RADIUS)
        self._card.addSubview_(tint)

        border = self._border = Quartz.CAGradientLayer.layer()
        border.setFrame_(card_rect)
        border.setStartPoint_((0.0, 0.5))
        border.setEndPoint_((1.0, 0.5))
        border.setColors_([_cg(0.25, 0.82, 1.0, 0.95), _cg(0.20, 0.45, 1.0, 0.30),
                           _cg(0.25, 0.82, 1.0, 0.95)])
        stroke = Quartz.CAShapeLayer.layer()
        stroke.setPath_(Quartz.CGPathCreateWithRoundedRect(
            ((0.75, 0.75), (CARD_W - 1.5, CARD_H - 1.5)), RADIUS - 0.75, RADIUS - 0.75, None))
        stroke.setLineWidth_(1.2)
        stroke.setFillColor_(None)
        stroke.setStrokeColor_(_cg(0, 0, 0))
        border.setMask_(stroke)
        tint.layer().addSublayer_(border)

        scan = Quartz.CAGradientLayer.layer()
        scan.setFrame_(((CARD_W * 0.3, CARD_H - 1.2), (CARD_W * 0.4, 1.2)))
        scan.setStartPoint_((0.0, 0.5))
        scan.setEndPoint_((1.0, 0.5))
        scan.setColors_([_cg(0.6, 0.95, 1.0, 0.0), _cg(0.75, 0.97, 1.0, 1.0),
                         _cg(0.6, 0.95, 1.0, 0.0)])
        tint.layer().addSublayer_(scan)

        self._build_orb()
        self._build_text()
        self._build_close(on_close)
        self._generation = 0
        self._spin = None

    def _ring(self, radius: float, width: float, dash: list[float] | None, alpha: float):
        ring = Quartz.CAShapeLayer.layer()
        ring.setBounds_(((0, 0), (BOX, BOX)))
        ring.setPosition_((BOX / 2, BOX / 2))
        ring.setPath_(Quartz.CGPathCreateWithEllipseInRect(
            ((BOX / 2 - radius, BOX / 2 - radius), (2 * radius, 2 * radius)), None))
        ring.setFillColor_(None)
        ring.setLineWidth_(width)
        ring.setOpacity_(alpha)
        if dash:
            ring.setLineDashPattern_(dash)
        self._box.layer().addSublayer_(ring)
        self._rings.append(ring)
        return ring

    def _build_orb(self) -> None:
        self._box = AppKit.NSView.alloc().initWithFrame_(((LEFT, (CARD_H - BOX) / 2), (BOX, BOX)))
        self._box.setWantsLayer_(True)
        self._card.addSubview_(self._box)
        self._rings = []

        self._glow = Quartz.CAGradientLayer.layer()
        self._glow.setType_(Quartz.kCAGradientLayerRadial)
        self._glow.setStartPoint_((0.5, 0.5))
        self._glow.setEndPoint_((1.0, 1.0))
        self._glow.setBounds_(((0, 0), (BOX, BOX)))
        self._glow.setPosition_((BOX / 2, BOX / 2))
        self._glow.setTransform_(Quartz.CATransform3DMakeScale(0.7, 0.7, 1.0))
        self._box.layer().addSublayer_(self._glow)

        self._outer = self._ring(23.5, 1.4, [16, 4, 4, 4], 0.95)
        self._ticks = self._ring(19.5, 3.0, [0.8, 2.2], 0.55)
        self._core = self._ring(13.0, 1.6, None, 1.0)
        self._core.setFillColor_(_cg(0.01, 0.05, 0.12, 0.95))
        self._core.setShadowOpacity_(1.0)
        self._core.setShadowRadius_(5)
        self._core.setShadowOffset_((0, 0))

        self._icon = AppKit.NSImageView.alloc().initWithFrame_((((BOX - 14) / 2, (BOX - 14) / 2),
                                                                (14, 14)))
        self._icon.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
        self._box.addSubview_(self._icon)

    def _build_text(self) -> None:
        x = LEFT + BOX + 12
        w = CARD_W - x - 36
        self._title = AppKit.NSTextField.labelWithString_("")
        self._title.setFrame_(((x, CARD_H - 23), (w, 14)))
        self._card.addSubview_(self._title)

        self._body = AppKit.NSTextField.wrappingLabelWithString_("")
        self._body.setFrame_(((x, 8), (w, 34)))
        self._body.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightRegular))
        self._body.setTextColor_(_ns(0.90, 0.95, 1.0))
        self._body.setMaximumNumberOfLines_(2)
        self._body.cell().setLineBreakMode_(AppKit.NSLineBreakByWordWrapping)
        self._body.cell().setTruncatesLastVisibleLine_(True)
        self._card.addSubview_(self._body)

    def _set_title(self, rgb) -> None:
        self._title.setAttributedStringValue_(AppKit.NSAttributedString.alloc().initWithString_attributes_(
            "JARVIS", {
                AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_weight_(
                    10.5, AppKit.NSFontWeightBold),
                AppKit.NSKernAttributeName: 2.4,
                AppKit.NSForegroundColorAttributeName: _ns(*rgb),
            }))

    def _build_close(self, on_close) -> None:
        self._close_target = _ClickTarget.alloc().initWithCallback_(on_close or self.dismiss)
        button = AppKit.NSButton.alloc().initWithFrame_(((CARD_W - 30, (CARD_H - 20) / 2), (20, 20)))
        button.setBordered_(False)
        button.setImage_(_symbol("xmark", 11, AppKit.NSFontWeightSemibold))
        button.setContentTintColor_(_ns(0.55, 0.75, 0.90))
        button.setTarget_(self._close_target)
        button.setAction_("clicked:")
        self._card.addSubview_(button)

    def _set_spin(self, seconds: float | None) -> None:
        if seconds == self._spin:
            return
        self._spin = seconds
        for ring, turn, pace in ((self._outer, -1, 1.0), (self._ticks, 1, 1.8)):
            ring.removeAnimationForKey_("spin")
            if seconds is None:
                continue
            spin = Quartz.CABasicAnimation.animationWithKeyPath_("transform.rotation.z")
            spin.setFromValue_(0.0)
            spin.setToValue_(turn * 2 * math.pi)
            spin.setDuration_(seconds * pace)
            spin.setRepeatCount_(float("inf"))
            ring.addAnimation_forKey_(spin, "spin")

    def _fade(self, alpha: float, seconds: float, then=None) -> None:
        def animate(context):
            context.setDuration_(seconds)
            self._panel.animator().setAlphaValue_(alpha)
        AppKit.NSAnimationContext.runAnimationGroup_completionHandler_(animate, then)

    def show(self, state: State, text: str) -> None:
        self._generation += 1
        body = f"“{text}”" if state is State.HEARD else (text or _DEFAULT_BODY.get(state, ""))
        self._body.setStringValue_(body)
        self._icon.setImage_(_symbol(_ICONS[state], 12, AppKit.NSFontWeightBold))
        rgb = _ACCENT[state]
        self._icon.setContentTintColor_(_ns(*rgb))
        for ring in self._rings:
            ring.setStrokeColor_(_cg(*rgb))
        self._core.setShadowColor_(_cg(*rgb))
        self._glow.setColors_([_cg(*rgb, 0.55), _cg(*rgb, 0.0)])
        self._card.layer().setShadowColor_(_cg(*rgb))
        self._border.setColors_([_cg(*rgb, 0.95), _cg(*rgb, 0.25), _cg(*rgb, 0.95)])
        self._set_title(rgb)
        self._set_spin(_SPIN_SECONDS.get(state, 8.0))
        if state is State.IDLE:
            self.level(0.0)
        if not self._panel.isVisible() or self._panel.alphaValue() < 1.0:
            self._panel.orderFrontRegardless()
            self._fade(1.0, 0.12)

    def level(self, value: float) -> None:
        scale = 0.7 + 0.45 * max(0.0, min(value, 1.0))
        self._glow.setTransform_(Quartz.CATransform3DMakeScale(scale, scale, 1.0))

    def dismiss(self) -> None:
        self._generation += 1
        generation = self._generation

        def gone():
            # Off screen entirely, not just transparent, so it cannot block clicks.
            if generation == self._generation:
                self._panel.orderOut_(None)
                self._set_spin(None)
        self._fade(0.0, 0.3, gone)

    def rest(self, text: str, after: float = 0.0) -> None:
        """Return to the idle card after a pause, unless something newer is showing by then."""
        generation = self._generation
        AppHelper.callLater(after, lambda: generation == self._generation
                            and self.show(State.IDLE, text))

    def hide(self, after: float = 0.0) -> None:
        generation = self._generation
        AppHelper.callLater(after, lambda: generation == self._generation and self.dismiss())
