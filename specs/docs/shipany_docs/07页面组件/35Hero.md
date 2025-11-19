
custom hero in page
page.tsx

import Hero from "@/components/blocks/hero";
import { Hero as HeroType } from "@/types/blocks/hero";
 
export default function Page() {
  // custom hero data
  const hero: HeroType = {
    title: "Ship Any AI Startups in hours, not days",
    highlight_text: "Ship Any",
    description:
      "ShipAny is a NextJS boilerplate for building AI SaaS startups.<br/>Ship Fast with a variety of templates and components.",
    announcement: {
      title: "🎉 Happy New Year",
      url: "/#pricing",
    },
    buttons: [
      {
        title: "Get ShipAny",
        url: "/ai-podcast-generator",
      },
    ],
    show_happy_users: true,
  };
 
  return <>
      <Hero hero={hero} />
      // ...other components
    </>
  );
}
Hero Type
types/blocks/hero.d.ts

export interface Hero {
  disabled?: boolean;
  title?: string;
  highlight_text?: string;
  description?: string;
  buttons?: Button[];
  image?: Image;
  announcement?: Announcement;
  show_happy_users?: boolean;
}
Last updated on 2025年1月5日