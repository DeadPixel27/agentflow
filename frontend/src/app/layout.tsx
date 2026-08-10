import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import { Toaster } from "sonner";

import { NavBar } from "@/components/nav-bar";
import { SignInProvider } from "@/hooks/use-sign-in";
import { UserProvider } from "@/hooks/use-user";
import { cn } from "@/lib/utils";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: "AgentFlow",
  description:
    "Upload documents, describe a task in plain English, and run an AI agent pipeline.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={cn(
          "min-h-screen font-sans antialiased",
          inter.variable,
          sourceSerif.variable,
        )}
      >
        <UserProvider>
          <SignInProvider>
            <div className="flex h-screen flex-col overflow-hidden bg-background">
              <NavBar />
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                {children}
              </div>
            </div>
            <Toaster richColors position="top-right" closeButton />
          </SignInProvider>
        </UserProvider>
      </body>
    </html>
  );
}
