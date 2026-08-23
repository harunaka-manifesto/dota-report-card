"use client";

import type { ReactNode } from "react";
import { useId } from "react";

export type GlyphCategory = "element" | "pattern";

export type GlyphDefinition = {
  key: string;
  category: GlyphCategory;
  name: string;
  palette: readonly [string, string];
  geometry: string;
};

type GlyphProps = {
  glyph: string;
  size?: number;
  className?: string;
  monochrome?: boolean;
  knockout?: boolean;
  /** Decorative when a nearby visible label already names the glyph. */
  decorative?: boolean;
};

type ShapeProps = { stroke: string; fill: string; gradientId: string };

const ELEMENTS: GlyphDefinition[] = [
  { key: "hero_pool_breadth", category: "element", name: "Breadth", palette: ["#2D6BFF", "#35D8E8"], geometry: "three-expanding-rays" },
  { key: "hero_pool_stability", category: "element", name: "Stability", palette: ["#68748F", "#9A9CFF"], geometry: "braced-central-square" },
  { key: "hero_exploration_rate", category: "element", name: "Exploration", palette: ["#7753F7", "#FF72C7"], geometry: "broken-orbit-escaping-dot" },
  { key: "toolkit_breadth", category: "element", name: "Toolkit", palette: ["#FFAE42", "#FF6D32"], geometry: "asymmetric-four-lobed-cross" },
  { key: "post_loss_familiarity_shift", category: "element", name: "Familiarity", palette: ["#FF806F", "#E83D6F"], geometry: "nested-returning-doorways" },
  { key: "role_breadth", category: "element", name: "Role", palette: ["#3D55D9", "#B39AFF"], geometry: "five-sector-tilted-pentagon" },
  { key: "combat_involvement", category: "element", name: "Involvement", palette: ["#FF9B31", "#FFE15B"], geometry: "converging-arrows-central-spark" },
  { key: "finisher_orientation", category: "element", name: "Finishing", palette: ["#E53F45", "#FF893E"], geometry: "closing-aperture" },
  { key: "death_exposure", category: "element", name: "Deaths", palette: ["#F0444F", "#4C323A"], geometry: "interrupted-descending-pillar" },
  { key: "off_pool_performance", category: "element", name: "Transfer", palette: ["#39D7D0", "#3276E9"], geometry: "offset-bridge-platforms" },
  { key: "off_pool_activity_stability", category: "element", name: "Presence", palette: ["#B5E85A", "#29B9A3"], geometry: "open-radiating-rings" },
  { key: "performance_volatility", category: "element", name: "Volatility", palette: ["#F450B5", "#8057E8"], geometry: "unequal-wave-broken-frame" },
  { key: "recent_form_shift", category: "element", name: "Form", palette: ["#7CE6BB", "#356ADD"], geometry: "tilted-rising-plane" },
  { key: "recent_activity_shift", category: "element", name: "Pace", palette: ["#FFD744", "#FF7B30"], geometry: "accelerating-diagonal-slashes" },
  { key: "session_length_tendency", category: "element", name: "Duration", palette: ["#76D67E", "#35D6D1"], geometry: "elongated-hourglass" },
  { key: "late_session_performance", category: "element", name: "Drift", palette: ["#BBA6FF", "#4E83DA"], geometry: "progressively-offset-bands" },
  { key: "post_loss_activity_shift", category: "element", name: "Tempo", palette: ["#FF5CC8", "#FF8744"], geometry: "alternating-beat-columns" },
  { key: "post_loss_performance_response", category: "element", name: "Recovery", palette: ["#5EE290", "#B9E83E"], geometry: "upward-rebound-path" },
];

const PATTERNS: GlyphDefinition[] = [
  { key: "same_playbook", category: "pattern", name: "Same Playbook", palette: ["#865CFF", "#40D8E8"], geometry: "different-tiles-shared-center" },
  { key: "comfort_edge", category: "pattern", name: "Comfort Edge", palette: ["#F06C89", "#FFD662"], geometry: "crossed-inner-square" },
  { key: "partial_transfer", category: "pattern", name: "Partial Transfer", palette: ["#3ED5D0", "#FA7F7A"], geometry: "half-dissolving-bridge" },
  { key: "versatile_core", category: "pattern", name: "Versatile Core", palette: ["#61D77C", "#4C79DC"], geometry: "unequal-hex-spokes" },
  { key: "proven_flexibility", category: "pattern", name: "Proven Flexibility", palette: ["#3F70E6", "#B7E04E"], geometry: "articulated-bending-lattice" },
  { key: "controlled_presence", category: "pattern", name: "Controlled Presence", palette: ["#B1E85A", "#28B9A5"], geometry: "field-square-brackets" },
  { key: "session_fade", category: "pattern", name: "Session Fade", palette: ["#FF9A40", "#8B5BE6"], geometry: "descending-arc-dimming-nodes" },
  { key: "session_rise", category: "pattern", name: "Session Rise", palette: ["#FFD749", "#3F8CE8"], geometry: "ascending-arc-brightening-nodes" },
  { key: "bounceback", category: "pattern", name: "Bounceback", palette: ["#48D78A", "#F79A47"], geometry: "compressed-spring-release" },
  { key: "performance_slide", category: "pattern", name: "Performance Slide", palette: ["#E54859", "#8052D8"], geometry: "descending-offset-slabs" },
  { key: "presence_tax", category: "pattern", name: "Presence Tax", palette: ["#FFD74A", "#E64953"], geometry: "ring-wedge-toll-bar" },
];

export const ELEMENT_GLYPHS: readonly GlyphDefinition[] = ELEMENTS;
export const PATTERN_GLYPHS: readonly GlyphDefinition[] = PATTERNS;
export const GLYPH_REGISTRY: readonly GlyphDefinition[] = [...ELEMENTS, ...PATTERNS];

export const GLYPH_BY_KEY: Readonly<Record<string, GlyphDefinition>> = Object.fromEntries(
  GLYPH_REGISTRY.map((definition) => [definition.key, definition])
);

/** Used by unit/e2e checks to guard the visual vocabulary against accidental duplicates. */
export function glyphRegistryIsUnique(): boolean {
  const keys = GLYPH_REGISTRY.map((definition) => definition.key);
  const geometries = GLYPH_REGISTRY.map((definition) => definition.geometry);
  return GLYPH_REGISTRY.length === 29
    && new Set(keys).size === keys.length
    && new Set(geometries).size === geometries.length;
}

export function Glyph({ glyph, size = 64, className, monochrome = false, knockout = false, decorative = false }: GlyphProps) {
  const definition = GLYPH_BY_KEY[glyph] ?? GLYPH_REGISTRY[0];
  const reactId = useId().replaceAll(":", "");
  const gradientId = `glyph-${reactId}-${definition.geometry}`;
  const [first, second] = definition.palette;
  const stroke = monochrome ? "currentColor" : `url(#${gradientId})`;
  const fill = monochrome ? "currentColor" : `url(#${gradientId})`;
  return (
    <svg
      className={`glyph glyph-${definition.category}${knockout ? " glyph-knockout" : ""}${className ? ` ${className}` : ""}`}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : definition.name}
      focusable="false"
    >
      {!decorative && <title>{definition.name}</title>}
      {!monochrome && <defs><linearGradient id={gradientId} x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse"><stop offset="0" stopColor={first} /><stop offset="1" stopColor={second} /></linearGradient></defs>}
      <GlyphShape geometry={definition.geometry} stroke={stroke} fill={fill} gradientId={gradientId} />
    </svg>
  );
}

function GlyphShape({ geometry, stroke, fill, gradientId }: { geometry: string } & ShapeProps): ReactNode {
  const line = { stroke, fill: "none", strokeWidth: 3, strokeLinecap: "square" as const, strokeLinejoin: "miter" as const, vectorEffect: "non-scaling-stroke" as const };
  const thin = { ...line, strokeWidth: 2 };
  const solid = { fill, stroke: "none" };
  switch (geometry) {
    case "three-expanding-rays": return <g {...line}><path d="M32 32 16 16M32 32 48 16M32 32 32 54" /><path d="M11 11h10M11 11v10M43 11h10M53 11v10M27 53h10" /></g>;
    case "braced-central-square": return <g {...line}><rect x="20" y="20" width="24" height="24" /><path d="M12 20h8M12 20v8M44 20h8M52 20v8M12 44h8M12 44v-8M44 44h8M52 44v-8" /></g>;
    case "broken-orbit-escaping-dot": return <g {...line}><path d="M21 14a22 22 0 1 0 27 15M42 47a22 22 0 0 1-25-3" /><path d="m42 15 10-2-4 9" /><circle cx="48" cy="11" r="3" fill={fill} stroke="none" /></g>;
    case "asymmetric-four-lobed-cross": return <path {...solid} d="M27 8h10l2 15 15-3 4 9-14 7 9 12-8 7-12-10-8 11-9-5 6-15-14-5 4-10 15 3Z" />;
    case "nested-returning-doorways": return <g {...line}><path d="M13 53V20l19-9 19 9v33" /><path d="M21 53V26l11-6 11 6v27" /><path d="M29 53V32l3-2 3 2v21" /></g>;
    case "five-sector-tilted-pentagon": return <g {...thin}><path d="m32 9 20 15-8 25H20l-8-25Z" /><path d="M32 9v23M52 24 32 32M44 49 32 32M20 49l12-17M12 24l20 8" /></g>;
    case "converging-arrows-central-spark": return <g {...line}><path d="M10 16h14l-5 5M10 48h14l-5-5M54 16H40l5 5M54 48H40l5-5" /><path d="m32 20 4 8 8 4-8 4-4 8-4-8-8-4 8-4Z" /></g>;
    case "closing-aperture": return <g {...line}><path d="M12 20 27 32 12 44M52 20 37 32l15 12M20 12l12 15 12-15M20 52l12-15 12 15" /><circle cx="32" cy="32" r="5" /></g>;
    case "interrupted-descending-pillar": return <g {...line}><path d="M18 10h13v14M46 54H33V40M33 24v6M33 34v6" /><path d="M18 54h13M46 10H33" /></g>;
    case "offset-bridge-platforms": return <g {...line}><path d="M10 46h16V34h12V22h16" /><path d="M10 52h18V40h12V28h14" /><path d="M18 22h12M40 46h10" /></g>;
    case "open-radiating-rings": return <g {...line}><circle cx="32" cy="32" r="8" /><path d="M32 18v-8M32 54v-8M18 32h-8M54 32h-8M22 22l-6-6M48 48l-6-6M42 22l6-6M16 48l6-6" /></g>;
    case "unequal-wave-broken-frame": return <g {...line}><path d="M12 22v-8h8M44 14h8v8M52 42v8h-8M20 50h-8v-8" /><path d="M14 35h8l4-16 7 28 5-20 5 8h7" /></g>;
    case "tilted-rising-plane": return <g {...line}><path d="m13 44 13-24 25 8-13 24Z" /><path d="M20 39 32 34l10 3" /></g>;
    case "accelerating-diagonal-slashes": return <g {...line}><path d="m13 46 8-17M25 49l12-25M40 50l12-30" /><path d="m18 20 5-6M30 17l5-6M44 14l5-6" /></g>;
    case "elongated-hourglass": return <g {...line}><path d="M20 11h24M20 53h24M23 12c0 9 9 12 9 20s-9 11-9 20M41 12c0 9-9 12-9 20s9 11 9 20" /></g>;
    case "progressively-offset-bands": return <g {...line}><path d="M12 18h30M17 28h30M22 38h30M27 48h25" /></g>;
    case "alternating-beat-columns": return <g {...solid}><path d="M11 25h8v23h-8zM22 15h8v33h-8zM34 30h8v18h-8zM45 20h8v28h-8z" /></g>;
    case "upward-rebound-path": return <g {...line}><path d="M12 46h10l5-15 7 8 8-20h10" /><path d="m42 19 10 0-5 7" /></g>;
    case "different-tiles-shared-center": return <g {...line}><rect x="10" y="10" width="12" height="12" /><path d="M42 10h12v12H42zM10 42h12v12H10zM42 42h12v12H42z" /><circle cx="32" cy="32" r="7" fill={fill} stroke="none" /><path d="M22 16h20M16 22v20M48 22v20M22 48h20" opacity=".45" /></g>;
    case "crossed-inner-square": return <g {...line}><rect x="18" y="18" width="28" height="28" /><path d="m11 11 42 42M53 11 11 53" /><rect x="26" y="26" width="12" height="12" fill={fill} stroke="none" /></g>;
    case "half-dissolving-bridge": return <g {...line}><path d="M10 42h16V28h14" /><path d="M44 28h5M53 28h2M42 42h7M53 42h2" /><circle cx="35" cy="28" r="2" fill={fill} stroke="none" /><circle cx="35" cy="42" r="2" fill={fill} stroke="none" /></g>;
    case "unequal-hex-spokes": return <g {...line}><path d="m32 11 18 10v22L32 53 14 43V21Z" /><path d="M32 32 32 11M32 32l18-11M32 32l18 22M32 32 14 43M32 32 14 21" /></g>;
    case "articulated-bending-lattice": return <g {...line}><path d="M10 18h13l8 10 10-10h13M10 46h13l8-10 10 10h13M23 18v28M41 18v28" /><circle cx="31" cy="28" r="3" fill={fill} stroke="none" /><circle cx="31" cy="36" r="3" fill={fill} stroke="none" /></g>;
    case "field-square-brackets": return <g {...line}><path d="M10 24v-10h10M44 14h10v10M54 40v10H44M20 50H10V40" /><circle cx="32" cy="32" r="8" /><circle cx="32" cy="32" r="17" strokeDasharray="3 5" /></g>;
    case "descending-arc-dimming-nodes": return <g {...line}><path d="M12 18c12 0 8 28 20 28 8 0 11-12 20-12" /><circle cx="12" cy="18" r="4" fill={fill} stroke="none" /><circle cx="32" cy="46" r="3" fill={fill} stroke="none" opacity=".7" /><circle cx="52" cy="34" r="2" fill={fill} stroke="none" opacity=".42" /></g>;
    case "ascending-arc-brightening-nodes": return <g {...line}><path d="M12 46c12 0 8-28 20-28 8 0 11 12 20 12" /><circle cx="12" cy="46" r="2" fill={fill} stroke="none" opacity=".42" /><circle cx="32" cy="18" r="3" fill={fill} stroke="none" opacity=".7" /><circle cx="52" cy="30" r="4" fill={fill} stroke="none" /></g>;
    case "compressed-spring-release": return <g {...line}><path d="M12 44h9l4-8-8-8 8-8-4-8h14l4 8-8 8 8 8-4 8h17" /><path d="m43 18 9 0-5 5" /></g>;
    case "descending-offset-slabs": return <g {...line}><path d="M12 15h25v9H12zM19 28h25v9H19zM26 41h25v9H26z" /><path d="M37 15v9M44 28v9M51 41v9" /></g>;
    case "ring-wedge-toll-bar": return <g {...line}><path d="M32 10a22 22 0 1 1-15 6" /><path d="m17 16 7 1-4 6" /><path d="M26 39h20" /><path d="M35 34v10" /></g>;
    default: return <circle {...line} cx="32" cy="32" r="22" />;
  }
}
