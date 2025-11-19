custom FAQ in page
page.tsx

import FAQ from "@/components/blocks/faq";
import { FAQ as FAQType } from "@/types/blocks/faq";
 
export default function Page() {
  // custom FAQ data
  const faq: FAQType = {
    "title": "FAQ",
    "description": "Frequently Asked Questions About ShipAny",
    "items": [
      {
        "question": "What exactly is ShipAny and how does it work?",
        "answer": "ShipAny is a comprehensive NextJS boilerplate designed specifically for building AI SaaS startups. It provides ready-to-use templates, infrastructure setup, and deployment tools that help you launch your AI business in hours instead of days."
      },
      // ...other questions
    ],
  };
 
  return <>
      <FAQ faq={faq} />
      // ...other components
    </>
  );
}
FAQ Type
types/blocks/faq.d.ts

export interface FAQItem {
  question?: string;
  answer?: string;
}
 
export interface FAQ {
  disabled?: boolean;
  title?: string;
  description?: string;
  items?: FAQItem[];
}
Last updated on 2025年1月5日