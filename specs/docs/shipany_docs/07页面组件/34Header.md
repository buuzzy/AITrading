custom header in page
page.tsx

import Header from "@/components/blocks/header";
import { Header as HeaderType } from "@/types/blocks/header";
 
export default function Page() {
  // custom header data
  const header: HeaderType = {
    logo: {
      title: "ShipAny",
      image: {
        src: "/logo.png",
        alt: "ShipAny",
      },
    },
    nav: {
      items: [
        {
          title: "Features",
          href: "/features",
        },
        {
          title: "Pricing",
          href: "/pricing",
        },
        {
          title: "Showcases",
          children: [
            {
              title: "Showcase 1",
              href: "/showcase/1",
            },
            {
              title: "Showcase 2",
              href: "/showcase/2",
            },
          ],
        },
      ],
    },
    buttons: [
      {
        title: "Sign In",
        variant: "primary",
        href: "/auth/signin",
      },
    ],
  };
 
  return (
    <>
      <Header header={header} />
      // ...other components
    </>
  );
}
Header Type
types/blocks/header.d.ts

export interface Header {
  disabled?: boolean;
  logo?: Logo;
  nav?: Nav;
  buttons?: Button[];
  className?: string;
}
Last updated on 2025年1月5日