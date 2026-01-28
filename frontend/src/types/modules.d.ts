// Type declarations for modules without TypeScript types

declare module '@tabler/icons-react' {
  import { FC, SVGProps } from 'react';
  
  export const IconArrowLeft: FC<SVGProps<SVGSVGElement>>;
  export const IconArrowRight: FC<SVGProps<SVGSVGElement>>;
  export const IconArrowNarrowLeft: FC<SVGProps<SVGSVGElement>>;
  export const IconArrowNarrowRight: FC<SVGProps<SVGSVGElement>>;
  export const IconX: FC<SVGProps<SVGSVGElement>>;
  export const IconUpload: FC<SVGProps<SVGSVGElement>>;
  export const IconLayoutNavbarCollapse: FC<SVGProps<SVGSVGElement>>;
  export const IconBrandGithub: FC<SVGProps<SVGSVGElement>>;
  export const IconBrandX: FC<SVGProps<SVGSVGElement>>;
  export const IconExchange: FC<SVGProps<SVGSVGElement>>;
  export const IconHome: FC<SVGProps<SVGSVGElement>>;
  export const IconNewSection: FC<SVGProps<SVGSVGElement>>;
  export const IconTerminal2: FC<SVGProps<SVGSVGElement>>;
  export const IconBrandApple: FC<SVGProps<SVGSVGElement>>;
  export const IconSearch: FC<SVGProps<SVGSVGElement>>;
  export const IconWorld: FC<SVGProps<SVGSVGElement>>;
  export const IconCommand: FC<SVGProps<SVGSVGElement>>;
  export const IconCaretRightFilled: FC<SVGProps<SVGSVGElement>>;
  export const IconCaretDownFilled: FC<SVGProps<SVGSVGElement>>;
  
  // Catch-all for other icons
  const icons: { [key: string]: FC<SVGProps<SVGSVGElement>> };
  export default icons;
}

declare module 'three-globe' {
  import { Object3D } from 'three';
  
  interface GlobeInstance extends Object3D {
    globeImageUrl(url: string): this;
    bumpImageUrl(url: string): this;
    backgroundImageUrl(url: string): this;
    showAtmosphere(show: boolean): this;
    atmosphereColor(color: string): this;
    atmosphereAltitude(altitude: number): this;
    hexPolygonsData(data: any[]): this;
    hexPolygonResolution(resolution: number): this;
    hexPolygonMargin(margin: number): this;
    hexPolygonUseDots(useDots: boolean): this;
    hexPolygonColor(colorFn: (d: any) => string): this;
    hexPolygonLabel(labelFn: (d: any) => string): this;
    arcsData(data: any[]): this;
    arcColor(colorFn: (e: any) => string): this;
    arcAltitude(altitudeFn: (e: any) => number): this;
    arcStroke(strokeFn: (e: any) => number): this;
    arcDashLength(length: number): this;
    arcDashInitialGap(gapFn: (e: any) => number): this;
    arcDashGap(gap: number): this;
    arcDashAnimateTime(timeFn: (e: any) => number): this;
    pointsData(data: any[]): this;
    pointColor(colorFn: (e: any) => string): this;
    pointsMerge(merge: boolean): this;
    pointAltitude(altitude: number): this;
    pointRadius(radius: number): this;
    ringsData(data: any[]): this;
    ringColor(colorFn: (t: number) => (e: any) => string): this;
    ringMaxRadius(radiusFn: (e: any) => number): this;
    ringPropagationSpeed(speedFn: (e: any) => number): this;
    ringRepeatPeriod(periodFn: (e: any) => number): this;
  }
  
  export default function ThreeGlobe(): GlobeInstance;
}
