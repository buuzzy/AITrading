custom CTA in page
page.tsx

import CTA from "@/components/blocks/cta";
import { CTA as CTAType } from "@/types/blocks/cta";
 
export default function Page() {
  // custom CTA data
  const cta: CTAType =  {
    "title": "Ship your first AI SaaS Startup",
    "description": "Start from here, with ShipAny.",
    "buttons": [
      {
        "title": "Get ShipAny",
        "url": "/#pricing"
      }
    ]
  }
 
  return <>
      <CTA cta={cta} />
      // ...other components
    </>
  );
}
CTA Type
types/blocks/cta.d.ts

import { Button } from "@/types/blocks/button";
 
export interface CTA {
  disabled?: boolean;
  title?: string;
  description?: string;
  buttons?: Button[];
}
Last updated on 2025年1月5日