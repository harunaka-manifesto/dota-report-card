"use client";

import type { ReactNode } from "react";
import { useId } from "react";

export type GlyphCategory = "element" | "family";

export type GlyphDefinition = {
  key: string;
  category: GlyphCategory;
  name: string;
  palette: readonly [string, string];
  geometry: string;
};

type ShapeProps = { stroke: string; fill: string };

const ELEMENTS: GlyphDefinition[] = [
  { key: "breadth", category: "element", name: "Breadth", palette: ["#2D6BFF", "#35D8E8"], geometry: "rays" },
  { key: "toolkit", category: "element", name: "Toolkit", palette: ["#FFAE42", "#FF6D32"], geometry: "cross" },
  { key: "involvement", category: "element", name: "Involvement", palette: ["#FF9B31", "#FFE15B"], geometry: "converging" },
  { key: "finishing", category: "element", name: "Finishing", palette: ["#E53F45", "#FF893E"], geometry: "aperture" },
  { key: "death_exposure", category: "element", name: "Death exposure", palette: ["#F0444F", "#4C323A"], geometry: "broken-pillar" },
  { key: "transfer", category: "element", name: "Transfer", palette: ["#39D7D0", "#3276E9"], geometry: "bridge" },
  { key: "consistency", category: "element", name: "Consistency", palette: ["#BBA6FF", "#4E83DA"], geometry: "bands" },
];

const FAMILIES: GlyphDefinition[] = [
  { key: "pool_shape", category: "family", name: "Pool shape", palette: ["#865CFF", "#40D8E8"], geometry: "orbit" },
  { key: "transfer_finding", category: "family", name: "Transfer finding", palette: ["#3ED5D0", "#FA7F7A"], geometry: "split-bridge" },
  { key: "post_loss_response", category: "family", name: "Post-loss response", palette: ["#48D78A", "#F79A47"], geometry: "rebound" },
  { key: "combat_expression", category: "family", name: "Combat expression", palette: ["#F450B5", "#8057E8"], geometry: "wave-frame" },
  { key: "session_drift", category: "family", name: "Session drift", palette: ["#FFD749", "#3F8CE8"], geometry: "curve" },
];

export const ELEMENT_GLYPHS: readonly GlyphDefinition[] = ELEMENTS;
export const FAMILY_GLYPHS: readonly GlyphDefinition[] = FAMILIES;
export const GLYPH_REGISTRY: readonly GlyphDefinition[] = [...ELEMENTS, ...FAMILIES];
export const GLYPH_BY_KEY: Readonly<Record<string, GlyphDefinition>> = Object.fromEntries(
  GLYPH_REGISTRY.map((definition) => [definition.key, definition]),
);

export function glyphRegistryIsUnique(): boolean {
  const keys = GLYPH_REGISTRY.map((definition) => definition.key);
  const geometries = GLYPH_REGISTRY.map((definition) => definition.geometry);
  return GLYPH_REGISTRY.length === 12
    && ELEMENTS.length === 7
    && FAMILIES.length === 5
    && new Set(keys).size === keys.length
    && new Set(geometries).size === geometries.length;
}

export function Glyph({ glyph, size = 64, className, monochrome = false, decorative = false }: {
  glyph: string;
  size?: number;
  className?: string;
  monochrome?: boolean;
  decorative?: boolean;
}) {
  const definition = GLYPH_BY_KEY[glyph] ?? GLYPH_REGISTRY[0];
  const reactId = useId().replaceAll(":", "");
  const gradientId = `v6-glyph-${reactId}-${definition.geometry}`;
  const [first, second] = definition.palette;
  const stroke = monochrome ? "currentColor" : `url(#${gradientId})`;
  const fill = monochrome ? "currentColor" : `url(#${gradientId})`;
  return (
    <svg
      className={`glyph glyph-${definition.category}${className ? ` ${className}` : ""}`}
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
      <GlyphShape geometry={definition.geometry} stroke={stroke} fill={fill} />
    </svg>
  );
}

function GlyphShape({ geometry, stroke, fill }: { geometry: string } & ShapeProps): ReactNode {
  const line = { stroke, fill: "none", strokeWidth: 3, strokeLinecap: "square" as const, strokeLinejoin: "miter" as const, vectorEffect: "non-scaling-stroke" as const };
  switch (geometry) {
    case "rays": return <g {...line}><path d="M32 32 15 15M32 32 49 15M32 32v23" /><path d="M11 11h10M11 11v10M43 11h10M53 11v10M27 55h10" /></g>;
    case "cross": return <path fill={fill} stroke="none" d="M27 8h10l2 15 15-3 4 9-14 7 9 12-8 7-12-10-8 11-9-5 6-15-14-5 4-10 15 3Z" />;
    case "converging": return <g {...line}><path d="M10 16h14l-5 5M10 48h14l-5-5M54 16H40l5 5M54 48H40l5-5" /><path d="m32 20 4 8 8 4-8 4-4 8-4-8-8-4 8-4Z" /></g>;
    case "aperture": return <g {...line}><path d="M12 20 27 32 12 44M52 20 37 32l15 12M20 12l12 15 12-15M20 52l12-15 12 15" /><circle cx="32" cy="32" r="5" /></g>;
    case "broken-pillar": return <g {...line}><path d="M18 10h13v14M46 54H33V40M33 24v6M33 34v6M18 54h13M46 10H33" /></g>;
    case "bridge": return <g {...line}><path d="M10 46h16V34h12V22h16M10 52h18V40h12V28h14" /><path d="M18 22h12M40 46h10" /></g>;
    case "bands": return <g {...line}><path d="M12 18h30M17 28h30M22 38h30M27 48h25" /></g>;
    case "orbit": return <g {...line}><path d="M21 14a22 22 0 1 0 27 15M42 47a22 22 0 0 1-25-3" /><path d="m42 15 10-2-4 9" /><circle cx="48" cy="11" r="3" fill={fill} stroke="none" /></g>;
    case "split-bridge": return <g {...line}><path d="M10 42h16V28h14M44 28h5M53 28h2M42 42h7M53 42h2" /><circle cx="35" cy="28" r="2" fill={fill} stroke="none" /><circle cx="35" cy="42" r="2" fill={fill} stroke="none" /></g>;
    case "rebound": return <g {...line}><path d="M12 46h10l5-15 7 8 8-20h10" /><path d="m42 19 10 0-5 7" /></g>;
    case "wave-frame": return <g {...line}><path d="M12 22v-8h8M44 14h8v8M52 42v8h-8M20 50h-8v-8" /><path d="M14 35h8l4-16 7 28 5-20 5 8h7" /></g>;
    case "curve": return <g {...line}><path d="M12 46c12 0 8-28 20-28 8 0 11 12 20 12" /><circle cx="12" cy="46" r="2" fill={fill} stroke="none" opacity=".42" /><circle cx="32" cy="18" r="3" fill={fill} stroke="none" opacity=".7" /><circle cx="52" cy="30" r="4" fill={fill} stroke="none" /></g>;
    default: return <circle {...line} cx="32" cy="32" r="22" />;
  }
}
