/**
 * Agency OS — Logo Reveal Module
 * "The Fold" — Wordmark to Monogram animation
 *
 * Stack: GSAP 3 + MorphSVGPlugin
 * Accessibility: respects prefers-reduced-motion
 *
 * Usage:
 *   import { logoReveal } from '@/lib/logo-reveal';
 *   const tl = logoReveal.init(containerElement, { onComplete: () => {} });
 *   logoReveal.replay(containerElement);
 *
 * Container must be a positioned element (position: relative or absolute).
 * The module injects its own DOM into the container.
 *
 * Sequence:
 *   0.00s  Hold wordmark "AgencyOS"
 *   0.35s  "gency" + "S" fade-drop (0.55s, power2.inOut)
 *   0.70s  A glides to centre, scales 3.2x (0.8s, power4.inOut)
 *   0.85s  O follows centre, scales 3.6x (0.6s, power4.inOut)
 *   1.38s  Swap text O for SVG O glyph (invisible)
 *   1.40s  O morphs to bar via MorphSVG (0.55s, power2.out)
 *   1.80s  SVG and text A fade out
 *   1.88s  Final mark (The Strike) fades in
 *   2.10s  onComplete callback fires
 *
 * Generated glyph: run node extract-glyph.js to replace O_GLYPH_PATH
 * with the exact Playfair Display 900 italic "O" path.
 */

import { gsap } from 'gsap';
import { MorphSVGPlugin } from 'gsap/MorphSVGPlugin';

gsap.registerPlugin(MorphSVGPlugin);

// ─── Pre-extracted Playfair Display 900 italic "O" glyph path ─────────────
// Approximated as a counter-aperture donut ellipse.
// Replace with exact glyph: node frontend/src/lib/logo-reveal/extract-glyph.js
// The path is defined in a 200x200 coordinate space (matches SVG viewBox).
const O_GLYPH_PATH =
  'M106,62 C128,60 146,78 147,100 C148,122 132,140 110,142 C88,144 70,126 69,104 C68,82 84,64 106,62 Z ' +
  'M106,76 C120,75 130,87 131,100 C132,113 122,125 108,126 C94,127 84,115 83,102 C82,89 92,77 106,76 Z';

// ─── The Strike bar path ───────────────────────────────────────────────────
// Horizontal rectangle in 200x200 SVG space.
// Specs: 54% from top, 11% height, extends 14% beyond letterform on each side.
// At EM_SQUARE=200, mid-point y ≈ 100. Bar height ≈ 22 units.
const BAR_PATH = 'M-40,89 L240,89 L240,111 L-40,111 Z';

// ─── Design tokens (kept in sync with CSS custom properties) ──────────────
const TOKENS = {
  amber: '#D4956A',
  ink:   '#0C0A08',
  cream: '#F7F3EE',
};

// ─── Default options ───────────────────────────────────────────────────────
const DEFAULTS = {
  autoplay:      true,
  delay:         400,       // ms before first play
  speed:         1,         // timeline speed multiplier
  reducedMotion: 'auto',    // 'auto' | 'skip' | 'play'
  onComplete:    () => {},
  taglineEl:     null,      // optional external tagline element to reveal
};

// ─── Internal state per container ─────────────────────────────────────────
const _state = new WeakMap();

// ═══════════════════════════════════════════════════════════════════════════
// DOM BUILDER
// Injects the required HTML structure into the provided container.
// Idempotent — clears existing inject before re-running.
// ═══════════════════════════════════════════════════════════════════════════
function buildDOM(container) {
  // Clear previous
  const existing = container.querySelector('.lra-root');
  if (existing) existing.remove();

  const root = document.createElement('div');
  root.className = 'lra-root';
  root.style.cssText = `
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  `;

  // Wordmark
  root.innerHTML = `
    <div class="lra-wordmark" style="
      position: absolute;
      font-family: 'Playfair Display', serif;
      font-weight: 700;
      font-size: 72px;
      letter-spacing: -0.022em;
      line-height: 1;
      color: ${TOKENS.ink};
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
    ">
      <span class="lra-l lra-a" style="display:inline-block;will-change:transform,opacity;position:relative;">A</span>
      <span class="lra-l lra-fade" style="display:inline-block;will-change:transform,opacity;">g</span>
      <span class="lra-l lra-fade" style="display:inline-block;will-change:transform,opacity;">e</span>
      <span class="lra-l lra-fade" style="display:inline-block;will-change:transform,opacity;">n</span>
      <span class="lra-l lra-fade" style="display:inline-block;will-change:transform,opacity;">c</span>
      <span class="lra-l lra-fade" style="display:inline-block;will-change:transform,opacity;">y</span>
      <span class="lra-l lra-o" style="display:inline-block;will-change:transform,opacity;font-style:italic;color:${TOKENS.amber};">O</span>
      <span class="lra-l lra-fade lra-s" style="display:inline-block;will-change:transform,opacity;font-style:italic;color:${TOKENS.amber};">S</span>
    </div>

    <svg class="lra-svg" style="
      position:absolute;top:0;left:0;width:100%;height:100%;
      pointer-events:none;overflow:visible;
    " viewBox="0 0 200 200" preserveAspectRatio="none">
      <path class="lra-o-glyph" d="${O_GLYPH_PATH}" fill="${TOKENS.amber}" opacity="0"/>
    </svg>

    <div class="lra-final" style="
      position:absolute;top:50%;left:50%;
      transform:translate(-50%,-50%);
      opacity:0;
    ">
      <span class="lra-mark-a" style="
        font-family:'Playfair Display',serif;
        font-weight:900;
        font-style:italic;
        font-size:140px;
        color:${TOKENS.ink};
        line-height:1;
        position:relative;
        display:block;
      ">A<span class="lra-mark-bar" style="
        position:absolute;
        left:-14%;right:-14%;
        top:54%;
        height:11%;
        background:${TOKENS.amber};
        transform:translateY(-50%);
        z-index:-1;
        display:block;
      "></span></span>
    </div>
  `;

  container.appendChild(root);
  return root;
}

// ═══════════════════════════════════════════════════════════════════════════
// CALIBRATION
// Measures letter positions relative to container centre.
// Must be called after fonts render and container is in layout.
// ═══════════════════════════════════════════════════════════════════════════
function calibrate(container) {
  const lA = container.querySelector('.lra-a');
  const lO = container.querySelector('.lra-o');

  // Reset transforms before measuring
  gsap.set([lA, lO], { clearProps: 'all' });
  void container.offsetWidth; // force reflow

  const cRect = container.getBoundingClientRect();
  const aRect = lA.getBoundingClientRect();
  const oRect = lO.getBoundingClientRect();

  const cx = cRect.left + cRect.width / 2;
  const cy = cRect.top  + cRect.height / 2;

  return {
    aDx: cx - (aRect.left + aRect.width  / 2),
    aDy: cy - (aRect.top  + aRect.height / 2),
    oDx: cx - (oRect.left + oRect.width  / 2),
    oDy: cy - (oRect.top  + oRect.height / 2),
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// TIMELINE BUILDER
// ═══════════════════════════════════════════════════════════════════════════
function buildTimeline(container, cal, opts) {
  const lA      = container.querySelector('.lra-a');
  const lO      = container.querySelector('.lra-o');
  const fades   = container.querySelectorAll('.lra-fade');
  const oGlyph  = container.querySelector('.lra-o-glyph');
  const final   = container.querySelector('.lra-final');

  const tl = gsap.timeline({
    paused:      true,
    timeScale:   opts.speed,
    onComplete() {
      opts.onComplete();
      if (opts.taglineEl) {
        gsap.to(opts.taglineEl, { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' });
      }
    },
    defaults: { ease: 'power4.inOut' },
  });

  // Phase 2 — Fade-drop "gency" + "S"
  tl.to(fades, {
    opacity:  0,
    y:        6,
    duration: 0.55,
    stagger:  0.018,
    ease:     'power2.inOut',
  }, 0.35);

  // Phase 3 — A glides to centre, scales 3.2x
  tl.to(lA, {
    x:        cal.aDx,
    y:        cal.aDy,
    scale:    3.2,
    duration: 0.8,
  }, 0.70);

  // Phase 4 — O follows centre, scales 3.6x (overlaps A by 0.3s)
  tl.to(lO, {
    x:        cal.oDx,
    y:        cal.oDy,
    scale:    3.6,
    duration: 0.6,
  }, 0.85);

  // Phase 5 — Swap text O for SVG O, then morph O → bar
  tl.call(() => {
    const lORect   = lO.getBoundingClientRect();
    const svgEl    = container.querySelector('.lra-svg');
    const svgRect  = svgEl.getBoundingClientRect();

    const screenCx = lORect.left + lORect.width  / 2;
    const screenCy = lORect.top  + lORect.height / 2;

    // Map screen coords to SVG viewBox coords (0-200 range)
    const svgCx = ((screenCx - svgRect.left) / svgRect.width)  * 200;
    const svgCy = ((screenCy - svgRect.top)  / svgRect.height) * 200;

    // Rendered size of O at scale 3.6
    const renderedW = lO.offsetWidth  * 3.6;
    const renderedH = lO.offsetHeight * 3.6;

    // The glyph path spans ~80 units in each axis (centred at 106, 102)
    const scaleX = renderedW / 80;
    const scaleY = renderedH / 80;
    const tx     = svgCx - 106 * scaleX;
    const ty     = svgCy - 102 * scaleY;

    gsap.set(oGlyph, {
      attr:    { transform: `translate(${tx},${ty}) scale(${scaleX},${scaleY})` },
      opacity: 1,
    });
    gsap.set(lO, { opacity: 0 });
  }, [], 1.38);

  // Phase 5b — MorphSVG: O glyph → bar
  tl.to(oGlyph, {
    duration: 0.55,
    ease:     'power2.out',
    morphSVG: { shape: BAR_PATH, type: 'rotational' },
  }, 1.40);

  // Phase 6 — Crossfade SVG + text A out, final mark in
  tl.to([oGlyph, lA], {
    opacity:  0,
    duration: 0.15,
    ease:     'power1.in',
  }, 1.80);

  tl.to(final, {
    opacity:  1,
    duration: 0.25,
    ease:     'power2.out',
  }, 1.88);

  return tl;
}

// ═══════════════════════════════════════════════════════════════════════════
// PUBLIC API
// ═══════════════════════════════════════════════════════════════════════════
export const logoReveal = {
  /**
   * init — build DOM, calibrate, and play the animation.
   *
   * @param {HTMLElement} container - Positioned element to inject into.
   * @param {object}      options   - Override defaults (see DEFAULTS above).
   * @returns {gsap.core.Timeline} The GSAP timeline (paused if autoplay: false).
   */
  init(container, options = {}) {
    const opts = { ...DEFAULTS, ...options };

    // Kill any existing timeline for this container
    const prev = _state.get(container);
    if (prev?.timeline) prev.timeline.kill();

    // Build DOM
    buildDOM(container);

    // Reduced motion gate
    const shouldSkip =
      opts.reducedMotion === 'skip' ||
      (opts.reducedMotion === 'auto' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    if (shouldSkip) {
      // Show final state immediately, fire callback
      const final = container.querySelector('.lra-final');
      const wm    = container.querySelector('.lra-wordmark');
      gsap.set(wm,    { opacity: 0 });
      gsap.set(final, { opacity: 1 });
      opts.onComplete();
      return null;
    }

    // Wait one frame for fonts/layout, then calibrate and build
    const tl = { _pending: true };
    _state.set(container, { timeline: null });

    requestAnimationFrame(() => {
      const cal    = calibrate(container);
      const gsapTl = buildTimeline(container, cal, opts);
      _state.set(container, { timeline: gsapTl, cal });

      if (opts.autoplay) {
        setTimeout(() => gsapTl.play(), opts.delay);
      }
    });

    return tl;
  },

  /**
   * replay — reset and replay the animation on an already-initialised container.
   *
   * @param {HTMLElement} container
   * @param {object}      options   - Optional override (uses last options if omitted).
   */
  replay(container, options = {}) {
    this.init(container, options);
  },

  /**
   * getTimeline — return the live GSAP timeline for a container.
   *
   * @param {HTMLElement} container
   * @returns {gsap.core.Timeline|null}
   */
  getTimeline(container) {
    return _state.get(container)?.timeline ?? null;
  },
};

export default logoReveal;
