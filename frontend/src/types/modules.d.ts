// Type declarations for modules without TypeScript types

declare module '@tabler/icons-react' {
  import { FC, SVGProps } from 'react';
  
  type IconComponent = FC<SVGProps<SVGSVGElement>>;
  
  export const IconArrowLeft: IconComponent;
  export const IconArrowRight: IconComponent;
  export const IconArrowNarrowLeft: IconComponent;
  export const IconArrowNarrowRight: IconComponent;
  export const IconX: IconComponent;
  export const IconUpload: IconComponent;
  export const IconLayoutNavbarCollapse: IconComponent;
  export const IconBrandGithub: IconComponent;
  export const IconBrandX: IconComponent;
  export const IconExchange: IconComponent;
  export const IconHome: IconComponent;
  export const IconNewSection: IconComponent;
  export const IconTerminal2: IconComponent;
  export const IconBrandApple: IconComponent;
  export const IconSearch: IconComponent;
  export const IconWorld: IconComponent;
  export const IconCommand: IconComponent;
  export const IconCaretRightFilled: IconComponent;
  export const IconCaretDownFilled: IconComponent;
  export const IconCaretUpFilled: IconComponent;
  export const IconDotsVertical: IconComponent;
  export const IconMicrophone: IconComponent;
  export const IconChevronUp: IconComponent;
  export const IconBrightnessUp: IconComponent;
  export const IconBrightnessDown: IconComponent;
}

declare module 'three-globe' {
  import { Object3D } from 'three';
  
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
    ringColor(colorFn: ((t: number) => (e: unknown) => string) | string): this;
    ringMaxRadius(radiusOrFn: number | ((e: unknown) => number)): this;
    ringPropagationSpeed(speedOrFn: number | ((e: unknown) => number)): this;
    ringRepeatPeriod(periodOrFn: number | ((e: unknown) => number)): this;
  }
  
  export default ThreeGlobe;
}
