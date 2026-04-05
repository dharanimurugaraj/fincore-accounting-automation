import { NextRequest, NextResponse } from 'next/server';

/**
 * Quick local authentication for production to prevent unwanted indexing or access.
 * Only triggers for the /login page as requested.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Only run in production
  // We check for 'production' but you can also use VERCEL_ENV if you want to include preview deployments
  if (process.env.NODE_ENV !== 'production' && process.env.VERCEL_ENV !== 'production') {
    return NextResponse.next();
  }

  // 2. Only run for the /login page
  if (pathname !== '/login') {
    return NextResponse.next();
  }

  // 3. One-time persistence check (Cookie)
  const authCookie = request.cookies.get('fincore_auth_session')?.value;
  if (authCookie === 'true') {
    return NextResponse.next();
  }

  const authHeader = request.headers.get('authorization');

  if (!authHeader) {
    return new NextResponse('Authentication required', {
      status: 401,
      headers: {
        'WWW-Authenticate': 'Basic realm="Secure Area"',
      },
    });
  }

  try {
    const authValue = authHeader.split(' ')[1];
    const decoded = atob(authValue);
    const [user, pass] = decoded.split(':');

    // Use environment variables for verification
    const correctUser = process.env.AUTH_USER || 'vyrenzo';
    const correctPass = process.env.AUTH_PASS || 'finance@1234';

    if (user === correctUser && pass === correctPass) {
      // SUCCESS: Set persistent cookie and allow through
      const response = NextResponse.next();
      response.cookies.set('fincore_auth_session', 'true', {
        maxAge: 60 * 60 * 24 * 30, // 30 days
        path: '/',
      });
      return response;
    }
  } catch (error) {
    // If decoding fails, return 401
  }

  return new NextResponse('Invalid credentials', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Secure Area"',
    },
  });
}

// Ensure the middleware only runs for the login path
export const config = {
  matcher: ['/login'],
};
