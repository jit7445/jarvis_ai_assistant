import math

import AppKit
import objc
import Quartz
from PyObjCTools import AppHelper

from jarvis.core.assistant import State

CARD_W, CARD_H = 520, 96
RADIUS = 22
PAD = 26
ORB = 54
HALO = 78
LEFT = 18

_DEFAULT_BODY = {State.LISTENING: "Listening…", State.THINKING: "Thinking…"}

_ICONS = {
    State.LISTENING: "mic.fill",
    State.THINKING: "waveform",
    State.HEARD: "waveform",
    State.CONFIRMING: "questionmark",
    State.DONE: "checkmark",
    State.FAILED: "exclamationmark",
}

_HALO_RGB = {
    State.LISTENING: (0.35, 0.55, 1.0),
    State.THINKING: (0.62, 0.40, 1.0),
    State.HEARD: (0.62, 0.40, 1.0),
    State.CONFIRMING: (1.0, 0.70, 0.25),
    State.DONE: (0.30, 0.85, 0.55),
    State.FAILED: (1.0, 0.40, 0.45),
}

_SPIN_SECONDS = {State.LISTENING: 4.0, State.THINKING: 1.2, State.HEARD: 1.2}


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
        p.setAlphaValue_(0.0)

        root = AppKit.NSView.alloc().initWithFrame_(((0, 0), (width, height)))
        p.setContentView_(root)

        card_rect = ((0, 0), (CARD_W, CARD_H))
        card_path = Quartz.CGPathCreateWithRoundedRect(card_rect, RADIUS, RADIUS, None)
        self._card = AppKit.NSView.alloc().initWithFrame_(((PAD, PAD), (CARD_W, CARD_H)))
        self._card.setWantsLayer_(True)
        glow = self._card.layer()
        glow.setShadowPath_(card_path)
        glow.setShadowColor_(_cg(0.50, 0.35, 1.0))
        glow.setShadowOpacity_(0.55)
        glow.setShadowRadius_(16)
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
        tint.layer().setBackgroundColor_(_cg(0.04, 0.05, 0.14, 0.62))
        tint.layer().setCornerRadius_(RADIUS)
        self._card.addSubview_(tint)

        border = Quartz.CAGradientLayer.layer()
        border.setFrame_(card_rect)
        border.setStartPoint_((0.0, 0.5))
        border.setEndPoint_((1.0, 0.5))
        border.setColors_([_cg(0.62, 0.40, 1.0, 0.95), _cg(0.30, 0.55, 1.0, 0.85),
                           _cg(0.62, 0.40, 1.0, 0.95)])
        stroke = Quartz.CAShapeLayer.layer()
        stroke.setPath_(Quartz.CGPathCreateWithRoundedRect(
            ((0.75, 0.75), (CARD_W - 1.5, CARD_H - 1.5)), RADIUS - 0.75, RADIUS - 0.75, None))
        stroke.setLineWidth_(1.5)
        stroke.setFillColor_(None)
        stroke.setStrokeColor_(_cg(0, 0, 0))
        border.setMask_(stroke)
        tint.layer().addSublayer_(border)

        self._build_orb()
        self._build_text()
        self._build_close(on_close)
        self._generation = 0
        self._spin = None

    def _build_orb(self) -> None:
        box = AppKit.NSView.alloc().initWithFrame_(((LEFT - (HALO - ORB) / 2, (CARD_H - HALO) / 2),
                                                    (HALO, HALO)))
        box.setWantsLayer_(True)
        self._card.addSubview_(box)
        center = (HALO / 2, HALO / 2)

        self._halo = Quartz.CALayer.layer()
        self._halo.setBounds_(((0, 0), (HALO, HALO)))
        self._halo.setPosition_(center)
        self._halo.setCornerRadius_(HALO / 2)
        self._halo.setTransform_(Quartz.CATransform3DMakeScale(0.75, 0.75, 1.0))
        box.layer().addSublayer_(self._halo)

        sphere = Quartz.CAGradientLayer.layer()
        sphere.setType_(Quartz.kCAGradientLayerRadial)
        sphere.setStartPoint_((0.35, 0.68))
        sphere.setEndPoint_((1.1, -0.1))
        sphere.setColors_([_cg(0.55, 0.85, 1.0), _cg(0.40, 0.45, 1.0), _cg(0.38, 0.16, 0.78)])
        sphere.setLocations_([0.0, 0.5, 1.0])
        sphere.setBounds_(((0, 0), (ORB, ORB)))
        sphere.setPosition_(center)
        sphere.setCornerRadius_(ORB / 2)
        sphere.setMasksToBounds_(True)
        sphere.setBorderWidth_(1.0)
        sphere.setBorderColor_(_cg(1, 1, 1, 0.25))
        box.layer().addSublayer_(sphere)

        self._shine = Quartz.CAGradientLayer.layer()
        self._shine.setType_(Quartz.kCAGradientLayerConic)
        self._shine.setStartPoint_((0.5, 0.5))
        self._shine.setEndPoint_((0.5, 0.0))
        self._shine.setColors_([_cg(1, 0.4, 0.75, 0.0), _cg(1, 0.4, 0.75, 0.45),
                                _cg(0.3, 0.9, 1.0, 0.0), _cg(0.3, 0.9, 1.0, 0.45),
                                _cg(1, 0.4, 0.75, 0.0)])
        self._shine.setBounds_(((0, 0), (ORB, ORB)))
        self._shine.setPosition_(center)
        self._shine.setCornerRadius_(ORB / 2)
        self._shine.setMasksToBounds_(True)
        box.layer().addSublayer_(self._shine)

        self._icon = AppKit.NSImageView.alloc().initWithFrame_((((HALO - 26) / 2, (HALO - 26) / 2),
                                                                (26, 26)))
        self._icon.setContentTintColor_(AppKit.NSColor.whiteColor())
        self._icon.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
        box.addSubview_(self._icon)

    def _build_text(self) -> None:
        x = LEFT + ORB + 18
        w = CARD_W - x - 52
        self._title = AppKit.NSTextField.labelWithString_("Jarvis")
        self._title.setFrame_(((x, CARD_H / 2 + 2), (w, 24)))
        self._title.setFont_(AppKit.NSFont.systemFontOfSize_weight_(17, AppKit.NSFontWeightBold))
        self._title.setTextColor_(AppKit.NSColor.whiteColor())
        self._card.addSubview_(self._title)

        self._body = AppKit.NSTextField.wrappingLabelWithString_("")
        self._body.setFrame_(((x, 12), (w, CARD_H / 2 - 12)))
        self._body.setFont_(AppKit.NSFont.systemFontOfSize_weight_(15, AppKit.NSFontWeightRegular))
        self._body.setTextColor_(_ns(0.88, 0.89, 0.95))
        self._body.setMaximumNumberOfLines_(2)
        self._body.cell().setLineBreakMode_(AppKit.NSLineBreakByTruncatingTail)
        self._card.addSubview_(self._body)

    def _build_close(self, on_close) -> None:
        self._close_target = _ClickTarget.alloc().initWithCallback_(on_close or self.dismiss)
        button = AppKit.NSButton.alloc().initWithFrame_(((CARD_W - 44, (CARD_H - 26) / 2), (26, 26)))
        button.setBordered_(False)
        button.setImage_(_symbol("xmark", 15, AppKit.NSFontWeightMedium))
        button.setContentTintColor_(_ns(0.75, 0.76, 0.85))
        button.setTarget_(self._close_target)
        button.setAction_("clicked:")
        self._card.addSubview_(button)

    def _set_spin(self, seconds: float | None) -> None:
        if seconds == self._spin:
            return
        self._spin = seconds
        self._shine.removeAnimationForKey_("spin")
        if seconds is None:
            return
        spin = Quartz.CABasicAnimation.animationWithKeyPath_("transform.rotation.z")
        spin.setFromValue_(0.0)
        spin.setToValue_(-2 * math.pi)
        spin.setDuration_(seconds)
        spin.setRepeatCount_(float("inf"))
        self._shine.addAnimation_forKey_(spin, "spin")

    def _fade(self, alpha: float, seconds: float, then=None) -> None:
        def animate(context):
            context.setDuration_(seconds)
            self._panel.animator().setAlphaValue_(alpha)
        AppKit.NSAnimationContext.runAnimationGroup_completionHandler_(animate, then)

    def show(self, state: State, text: str) -> None:
        self._generation += 1
        body = f"“{text}”" if state is State.HEARD else (text or _DEFAULT_BODY.get(state, ""))
        self._body.setStringValue_(body)
        self._icon.setImage_(_symbol(_ICONS[state], 20))
        r, g, b = _HALO_RGB[state]
        self._halo.setBackgroundColor_(_cg(r, g, b, 0.40))
        self._card.layer().setShadowColor_(_cg(r, g, b))
        self._set_spin(_SPIN_SECONDS.get(state, 8.0))
        if not self._panel.isVisible() or self._panel.alphaValue() < 1.0:
            self._panel.orderFrontRegardless()
            self._fade(1.0, 0.12)

    def level(self, value: float) -> None:
        scale = 0.75 + 0.5 * max(0.0, min(value, 1.0))
        self._halo.setTransform_(Quartz.CATransform3DMakeScale(scale, scale, 1.0))

    def dismiss(self) -> None:
        self._generation += 1
        generation = self._generation

        def gone():
            # Off screen entirely, not just transparent, so it cannot block clicks.
            if generation == self._generation:
                self._panel.orderOut_(None)
                self._set_spin(None)
        self._fade(0.0, 0.3, gone)

    def hide(self, after: float = 0.0) -> None:
        generation = self._generation
        AppHelper.callLater(after, lambda: generation == self._generation and self.dismiss())
