import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/auth/AuthContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FinCore — Banking Intelligence Platform",
  description:
    "AI-powered banking report automation for working capital management",
  icons: {
    icon: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased text-gray-900 bg-white`}>
        <AuthProvider>
           {children}
        </AuthProvider>
      </body>
    </html>
  );
}
