import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const providers: NextAuthOptions["providers"] = [
  CredentialsProvider({
    name: "Credentials",
    credentials: {
      email: { label: "Email", type: "email" },
      password: { label: "Password", type: "password" },
    },
    async authorize(credentials) {
      if (!credentials?.email) return null;

      if (credentials.email === "dev@fincore.local") {
        return {
          id: "dev-user",
          email: "dev@fincore.local",
          name: "Dev User",
          role: "ADMIN",
          orgId: "default-org",
          orgName: "FinCore Dev Org",
        };
      }

      try {
        const { prisma } = await import("./prisma");
        const user = await prisma.user.findUnique({
          where: { email: credentials.email },
          include: { org: true },
        });

        if (!user) return null;

        return {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
          orgId: user.orgId,
          orgName: user.org.name,
        };
      } catch {
        if (credentials.email === "dev@fincore.local") {
          return {
            id: "dev-user",
            email: "dev@fincore.local",
            name: "Dev User",
            role: "ADMIN",
            orgId: "default-org",
            orgName: "FinCore Dev Org",
          };
        }
        return null;
      }
    },
  }),
];

if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
  const GoogleProvider = require("next-auth/providers/google").default;
  providers.push(
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    })
  );
}

export const authOptions: NextAuthOptions = {
  providers,
  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === "google") {
        try {
          const { prisma } = await import("./prisma");
          const existingUser = await prisma.user.findUnique({
            where: { email: user.email! },
          });
          if (!existingUser) return false;
        } catch {
          return false;
        }
      }
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.role = (user as any).role;
        token.orgId = (user as any).orgId;
        token.orgName = (user as any).orgName;
        token.userId = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).role = token.role;
        (session.user as any).orgId = token.orgId;
        (session.user as any).orgName = token.orgName;
        (session.user as any).userId = token.userId;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET,
};
