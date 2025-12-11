import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";
import { auth } from "./auth";
import { NextResponse } from "next/server";

const intlMiddleware = createMiddleware(routing);

export default auth((req) => {
  const isAuth = !!req.auth;
  const { pathname } = req.nextUrl;

  // Explicitly protect /backtest routes (including localized versions like /zh/backtest)
  if (pathname.includes('/backtest')) {
    if (!isAuth) {
      // Redirect to sign-in page, preserving the return URL
      const signInUrl = new URL("/auth/signin", req.url);
      signInUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(signInUrl);
    }
  }

  return intlMiddleware(req);
});

export const config = {
  matcher: [
    "/",
    "/(en|en-US|zh|zh-CN|zh-TW|zh-HK|zh-MO|ja|ko|ru|fr|de|ar|es|it)/:path*",
    "/((?!api|_next|_vercel|.*\\..*).*)",
  ],
};
