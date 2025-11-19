custom Feature in page
page.tsx

import Feature from "@/components/blocks/feature";
import { Feature as FeatureType } from "@/types/blocks/feature";
 
export default function Page() {
  // custom Feature data
  const feature: FeatureType = {
    "title": "Key Features of ShipAny",
    "description": "Everything you need to launch your AI SaaS startup quickly and efficiently.",
    "items": [
      {
        "title": "Next.js Boilerplate",
        "description": "Production-ready Next.js templates with SEO-friendly structure and i18n support.",
        "icon": "Sparkles"
      },
      // ...other features
    ],
  };
 
  return <>
      <Feature feature={feature} />
      // ...other components
    </>
  );
}
Feature Type
types/blocks/feature.d.ts

import { Image } from "@/types/blocks/image";
 
export interface FeatureItem {
  title: string;
  description: string;
  icon?: string;
  image?: Image;
}
 
export interface Feature {
  title: string;
  description: string;
  items: FeatureItem[];
}
Last updated on 2025年1月5日