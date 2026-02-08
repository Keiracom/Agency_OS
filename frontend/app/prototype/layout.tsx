/**
 * Prototype Layout - Glass Sydney Theme
 * 
 * Provides the glassmorphic background with Sydney CBD night aesthetic.
 * All prototype pages inherit this layout.
 */

export default function PrototypeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen">
      {/* Background Layer - Sydney CBD Night */}
      <div 
        className="fixed inset-0 z-0"
        style={{
          backgroundImage: `
            linear-gradient(to bottom, rgba(0,0,0,0.7), rgba(15,23,42,0.85)),
            url('/images/sydney-cbd-night.jpg')
          `,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundAttachment: 'fixed',
        }}
      />
      
      {/* Blur overlay for glass effect foundation */}
      <div 
        className="fixed inset-0 z-0 backdrop-blur-[2px]"
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.4)',
        }}
      />
      
      {/* Content Layer */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
