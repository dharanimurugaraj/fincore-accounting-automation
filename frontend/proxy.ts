import { NextRequest, NextResponse } from 'next/server';

/**
 * Quick local authentication for production to prevent unwanted indexing or access.
 * Only triggers for the /login page as requested.
 */
export function proxy(request: NextRequest) {
  // HTTP Basic Auth has been disabled to allow public access to the login page.
  return NextResponse.next();
}

// Ensure the middleware only runs for the login path
export const config = {
  matcher: ['/login'],
};
