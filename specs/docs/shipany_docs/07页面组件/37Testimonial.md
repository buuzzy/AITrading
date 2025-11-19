custom Testimonial in page
page.tsx

import Testimonial from "@/components/blocks/testimonial";
import { Testimonial as TestimonialType } from "@/types/blocks/testimonial";
 
export default function Page() {
  // custom Testimonial data
  const testimonial: TestimonialType = {
    "title": "What Users Say About ShipAny",
    "description": "Hear from developers and founders who launched their AI startups with ShipAny.",
    "items": [
      {
        "avatar": {
          "src": "/imgs/user/1.png"
        },
        "name": "David Chen",
        "title": "Founder of AIWallpaper.shop",
        "comment": "ShipAny saved us months of development time. We launched our AI wallpaper business in just 2 days and got our first paying customer within a week!",
      },
      // ...other testimonials
    ],
  };
 
  return <>
      <Testimonial testimonial={testimonial} />
      // ...other components
    </>
  );
}
Testimonial Type
types/blocks/testimonial.d.ts

import { Image } from "@/types/blocks/image";
 
export interface TestimonialItem {
  avatar?: Image;
  name?: string;
  title?: string;
  comment?: string;
}
 
export interface Testimonial {
  disabled?: boolean;
  title?: string;
  description?: string;
  items?: TestimonialItem[];
}
Last updated on 2025年1月5日