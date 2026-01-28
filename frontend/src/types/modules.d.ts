// Type declarations for modules without TypeScript types

// Accept any icon from @tabler/icons-react
declare module '@tabler/icons-react' {
  import { FC, SVGProps } from 'react';
  type IconComponent = FC<SVGProps<SVGSVGElement>>;
  const value: { [key: string]: IconComponent };
  export = value;
}

declare module 'three-globe' {
  import { Object3D, Material } from 'three';
  
  class ThreeGlobe extends Object3D {
    constructor();
    globeImageUrl(url: string): this;
    bumpImageUrl(url: string): this;
    backgroundImageUrl(url: string): this;
    showAtmosphere(show: boolean): this;
    atmosphereColor(color: string): this;
    atmosphereAltitude(altitude: number): this;
    hexPolygonsData(data: unknown[]): this;
    hexPolygonResolution(resolution: number): this;
    hexPolygonMargin(margin: number): this;
    hexPolygonUseDots(useDots: boolean): this;
    hexPolygonColor(colorFn: (d: unknown) => string): this;
    hexPolygonLabel(labelFn: (d: unknown) => string): this;
    arcsData(data: unknown[]): this;
    arcStartLat(fn: (d: unknown) => number): this;
    arcStartLng(fn: (d: unknown) => number): this;
    arcEndLat(fn: (d: unknown) => number): this;
    arcEndLng(fn: (d: unknown) => number): this;
    arcColor(colorFn: (e: unknown) => string): this;
    arcAltitude(altitudeFn: (e: unknown) => number): this;
    arcStroke(strokeFn: () => number): this;
    arcDashLength(length: number): this;
    arcDashInitialGap(gapFn: (e: unknown) => number): this;
    arcDashGap(gap: number): this;
    arcDashAnimateTime(timeFn: () => number): this;
    pointsData(data: unknown[]): this;
    pointColor(colorOrFn: string | ((e: unknown) => string)): this;
    pointsMerge(merge: boolean): this;
    pointAltitude(altitude: number): this;
    pointRadius(radius: number): this;
    ringsData(data: unknown[]): this;
    ringColor(colorFn: (() => string) | string | ((t: number) => (e: unknown) => string)): this;
    ringMaxRadius(radiusOrFn: number | ((e: unknown) => number)): this;
    ringPropagationSpeed(speedOrFn: number | ((e: unknown) => number)): this;
    ringRepeatPeriod(periodOrFn: number | ((e: unknown) => number)): this;
    globeMaterial(): Material;
  }
  
  export default ThreeGlobe;
}
