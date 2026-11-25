import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Shell } from "@/components/Shell";
import { DemoProvider } from "@/lib/demo";
import "./globals.css";

export const metadata: Metadata = {
  title: "FaceLock Stego",
  description: "Face-recognition protected image steganography: AES-256-GCM + keyed random LSB + live face vault.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <DemoProvider>
          <Shell>{children}</Shell>
        </DemoProvider>
      </body>
    </html>
  );
}
