import { TopNav, BottomNav } from '@/components/Navigation';

export const metadata = {
  title: 'Elliot Dashboard',
  description: 'Agent monitoring and memory browser',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
    viewportFit: 'cover',
  },
};

export default function ElliotLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <TopNav />
      <main className="max-w-2xl mx-auto px-4 pb-24">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
