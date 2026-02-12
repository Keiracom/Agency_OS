import type { Metadata } from "next"
import "./globals.css"
import { Sidebar } from "@/components/dashboard/sidebar"

export const metadata: Metadata = {
  title: "Agency OS - Dashboard",
  description: "The Bloomberg Terminal for Client Acquisition",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
