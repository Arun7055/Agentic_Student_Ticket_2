import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// 1. Define the routes that require logging in
const isProtectedRoute = createRouteMatcher(['/portal(.*)']);

// 2. The Bouncer logic (Now Async!)
export default clerkMiddleware(async (auth, request) => {
  if (isProtectedRoute(request)) {
    await auth.protect(); // Wait for the promise and trigger the protection redirect
  }
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};