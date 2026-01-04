"use client";

export default function LogoShowcasePage() {
  return (
    <div className="min-h-screen bg-gray-100 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-2 text-gray-900">
          Agency OS Logo Options
        </h1>
        <p className="text-center text-gray-600 mb-12">
          Compare all variations side by side
        </p>

        {/* OPTION A - Clean Wordmark */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800 border-b pb-2">
            Option A - Clean Wordmark (No Icon)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* A1 - Solid Black/White */}
            <LogoCard label="A1 - Solid Text">
              <div className="space-y-8">
                {/* Full size */}
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <span className="text-5xl font-bold tracking-tight text-black">AOS</span>
                    <span className="text-sm font-light text-gray-600 tracking-widest uppercase mt-1">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                {/* Nav size */}
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold tracking-tight text-black">AOS</span>
                    <span className="text-xs font-light text-gray-500 tracking-wider">
                      Agency Operating System
                    </span>
                  </div>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="A1 - Solid Text (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <span className="text-5xl font-bold tracking-tight text-white">AOS</span>
                    <span className="text-sm font-light text-gray-400 tracking-widest uppercase mt-1">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold tracking-tight text-white">AOS</span>
                    <span className="text-xs font-light text-gray-500 tracking-wider">
                      Agency Operating System
                    </span>
                  </div>
                </div>
              </div>
            </LogoCardDark>

            {/* A2 - Gradient Text */}
            <LogoCard label="A2 - Gradient Text">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <span className="text-5xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      AOS
                    </span>
                    <span className="text-sm font-light text-gray-600 tracking-widest uppercase mt-1">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      AOS
                    </span>
                    <span className="text-xs font-light text-gray-500 tracking-wider">
                      Agency Operating System
                    </span>
                  </div>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="A2 - Gradient Text (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <span className="text-5xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                      AOS
                    </span>
                    <span className="text-sm font-light text-gray-400 tracking-widest uppercase mt-1">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                      AOS
                    </span>
                    <span className="text-xs font-light text-gray-500 tracking-wider">
                      Agency Operating System
                    </span>
                  </div>
                </div>
              </div>
            </LogoCardDark>
          </div>
        </section>

        {/* OPTION B - Geometric Icon + Wordmark */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800 border-b pb-2">
            Option B - Geometric Icon + Wordmark
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* B1 - Rounded Square */}
            <LogoCard label="B1 - Rounded Square">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                      <span className="text-white font-bold text-lg">A</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-3xl font-bold tracking-tight text-black">AOS</span>
                      <span className="text-xs font-light text-gray-500 tracking-wider uppercase">
                        Agency Operating System
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                      <span className="text-white font-bold text-sm">A</span>
                    </div>
                    <span className="text-xl font-bold tracking-tight text-black">AOS</span>
                  </div>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="B1 - Rounded Square (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                      <span className="text-white font-bold text-lg">A</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-3xl font-bold tracking-tight text-white">AOS</span>
                      <span className="text-xs font-light text-gray-400 tracking-wider uppercase">
                        Agency Operating System
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                      <span className="text-white font-bold text-sm">A</span>
                    </div>
                    <span className="text-xl font-bold tracking-tight text-white">AOS</span>
                  </div>
                </div>
              </div>
            </LogoCardDark>

            {/* B2 - Hexagon */}
            <LogoCard label="B2 - Hexagon">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex items-center gap-3">
                    <svg width="48" height="48" viewBox="0 0 48 48" className="flex-shrink-0">
                      <defs>
                        <linearGradient id="hexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#2563eb" />
                          <stop offset="100%" stopColor="#9333ea" />
                        </linearGradient>
                      </defs>
                      <path
                        d="M24 2 L44 14 L44 34 L24 46 L4 34 L4 14 Z"
                        fill="url(#hexGrad)"
                      />
                      <text x="24" y="29" textAnchor="middle" fill="white" fontWeight="bold" fontSize="16">A</text>
                    </svg>
                    <div className="flex flex-col">
                      <span className="text-3xl font-bold tracking-tight text-black">AOS</span>
                      <span className="text-xs font-light text-gray-500 tracking-wider uppercase">
                        Agency Operating System
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 48 48" className="flex-shrink-0">
                      <path
                        d="M24 2 L44 14 L44 34 L24 46 L4 34 L4 14 Z"
                        fill="url(#hexGrad)"
                      />
                      <text x="24" y="29" textAnchor="middle" fill="white" fontWeight="bold" fontSize="16">A</text>
                    </svg>
                    <span className="text-xl font-bold tracking-tight text-black">AOS</span>
                  </div>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="B2 - Hexagon (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex items-center gap-3">
                    <svg width="48" height="48" viewBox="0 0 48 48" className="flex-shrink-0">
                      <defs>
                        <linearGradient id="hexGradDark" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#3b82f6" />
                          <stop offset="100%" stopColor="#a855f7" />
                        </linearGradient>
                      </defs>
                      <path
                        d="M24 2 L44 14 L44 34 L24 46 L4 34 L4 14 Z"
                        fill="url(#hexGradDark)"
                      />
                      <text x="24" y="29" textAnchor="middle" fill="white" fontWeight="bold" fontSize="16">A</text>
                    </svg>
                    <div className="flex flex-col">
                      <span className="text-3xl font-bold tracking-tight text-white">AOS</span>
                      <span className="text-xs font-light text-gray-400 tracking-wider uppercase">
                        Agency Operating System
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 48 48" className="flex-shrink-0">
                      <path
                        d="M24 2 L44 14 L44 34 L24 46 L4 34 L4 14 Z"
                        fill="url(#hexGradDark)"
                      />
                      <text x="24" y="29" textAnchor="middle" fill="white" fontWeight="bold" fontSize="16">A</text>
                    </svg>
                    <span className="text-xl font-bold tracking-tight text-white">AOS</span>
                  </div>
                </div>
              </div>
            </LogoCardDark>

            {/* B3 - Abstract A Shape */}
            <LogoCard label="B3 - Abstract A">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex items-center gap-3">
                    <svg width="48" height="48" viewBox="0 0 48 48" className="flex-shrink-0">
                      <defs>
                        <linearGradient id="absGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#2563eb" />
                          <stop offset="100%" stopColor="#9333ea" />
                        </linearGradient>
                      </defs>
                      <path
                        d="M24 4 L42 44 L32 44 L28 34 L20 34 L16 44 L6 44 L24 4 Z M24 18 L21 28 L27 28 L24 18 Z"
                        fill="url(#absGrad)"
                        fillRule="evenodd"
                      />
                    </svg>
                    <div className="flex flex-col">
                      <span className="text-3xl font-bold tracking-tight text-black">AOS</span>
                      <span className="text-xs font-light text-gray-500 tracking-wider uppercase">
                        Agency Operating System
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 48 48" className="flex-shrink-0">
                      <path
                        d="M24 4 L42 44 L32 44 L28 34 L20 34 L16 44 L6 44 L24 4 Z M24 18 L21 28 L27 28 L24 18 Z"
                        fill="url(#absGrad)"
                        fillRule="evenodd"
                      />
                    </svg>
                    <span className="text-xl font-bold tracking-tight text-black">AOS</span>
                  </div>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="B3 - Abstract A (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex items-center gap-3">
                    <svg width="48" height="48" viewBox="0 0 48 48" className="flex-shrink-0">
                      <defs>
                        <linearGradient id="absGradDark" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#3b82f6" />
                          <stop offset="100%" stopColor="#a855f7" />
                        </linearGradient>
                      </defs>
                      <path
                        d="M24 4 L42 44 L32 44 L28 34 L20 34 L16 44 L6 44 L24 4 Z M24 18 L21 28 L27 28 L24 18 Z"
                        fill="url(#absGradDark)"
                        fillRule="evenodd"
                      />
                    </svg>
                    <div className="flex flex-col">
                      <span className="text-3xl font-bold tracking-tight text-white">AOS</span>
                      <span className="text-xs font-light text-gray-400 tracking-wider uppercase">
                        Agency Operating System
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 48 48" className="flex-shrink-0">
                      <path
                        d="M24 4 L42 44 L32 44 L28 34 L20 34 L16 44 L6 44 L24 4 Z M24 18 L21 28 L27 28 L24 18 Z"
                        fill="url(#absGradDark)"
                        fillRule="evenodd"
                      />
                    </svg>
                    <span className="text-xl font-bold tracking-tight text-white">AOS</span>
                  </div>
                </div>
              </div>
            </LogoCardDark>
          </div>
        </section>

        {/* OPTION C - Stylized Lettermark */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800 border-b pb-2">
            Option C - Stylized Lettermark
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* C1 - Connected Letters */}
            <LogoCard label="C1 - Connected Letters">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <svg width="180" height="60" viewBox="0 0 180 60" className="mb-1">
                      <defs>
                        <linearGradient id="connGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#2563eb" />
                          <stop offset="100%" stopColor="#9333ea" />
                        </linearGradient>
                      </defs>
                      {/* A */}
                      <path d="M10 50 L30 10 L50 50 M18 38 L42 38" stroke="url(#connGrad)" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      {/* O - connected to A */}
                      <ellipse cx="90" cy="30" rx="25" ry="22" stroke="url(#connGrad)" strokeWidth="6" fill="none"/>
                      {/* Connection line A to O */}
                      <line x1="50" y1="50" x2="65" y2="30" stroke="url(#connGrad)" strokeWidth="3" strokeLinecap="round"/>
                      {/* S - connected to O */}
                      <path d="M130 18 C150 10 165 20 155 32 C145 44 165 54 145 50" stroke="url(#connGrad)" strokeWidth="6" fill="none" strokeLinecap="round"/>
                      {/* Connection line O to S */}
                      <line x1="115" y1="30" x2="130" y2="22" stroke="url(#connGrad)" strokeWidth="3" strokeLinecap="round"/>
                    </svg>
                    <span className="text-xs font-light text-gray-500 tracking-wider uppercase">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <svg width="100" height="32" viewBox="0 0 180 60">
                    <path d="M10 50 L30 10 L50 50 M18 38 L42 38" stroke="url(#connGrad)" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                    <ellipse cx="90" cy="30" rx="25" ry="22" stroke="url(#connGrad)" strokeWidth="6" fill="none"/>
                    <line x1="50" y1="50" x2="65" y2="30" stroke="url(#connGrad)" strokeWidth="3" strokeLinecap="round"/>
                    <path d="M130 18 C150 10 165 20 155 32 C145 44 165 54 145 50" stroke="url(#connGrad)" strokeWidth="6" fill="none" strokeLinecap="round"/>
                    <line x1="115" y1="30" x2="130" y2="22" stroke="url(#connGrad)" strokeWidth="3" strokeLinecap="round"/>
                  </svg>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="C1 - Connected Letters (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <svg width="180" height="60" viewBox="0 0 180 60" className="mb-1">
                      <defs>
                        <linearGradient id="connGradDark" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#3b82f6" />
                          <stop offset="100%" stopColor="#a855f7" />
                        </linearGradient>
                      </defs>
                      <path d="M10 50 L30 10 L50 50 M18 38 L42 38" stroke="url(#connGradDark)" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      <ellipse cx="90" cy="30" rx="25" ry="22" stroke="url(#connGradDark)" strokeWidth="6" fill="none"/>
                      <line x1="50" y1="50" x2="65" y2="30" stroke="url(#connGradDark)" strokeWidth="3" strokeLinecap="round"/>
                      <path d="M130 18 C150 10 165 20 155 32 C145 44 165 54 145 50" stroke="url(#connGradDark)" strokeWidth="6" fill="none" strokeLinecap="round"/>
                      <line x1="115" y1="30" x2="130" y2="22" stroke="url(#connGradDark)" strokeWidth="3" strokeLinecap="round"/>
                    </svg>
                    <span className="text-xs font-light text-gray-400 tracking-wider uppercase">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <svg width="100" height="32" viewBox="0 0 180 60">
                    <path d="M10 50 L30 10 L50 50 M18 38 L42 38" stroke="url(#connGradDark)" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                    <ellipse cx="90" cy="30" rx="25" ry="22" stroke="url(#connGradDark)" strokeWidth="6" fill="none"/>
                    <line x1="50" y1="50" x2="65" y2="30" stroke="url(#connGradDark)" strokeWidth="3" strokeLinecap="round"/>
                    <path d="M130 18 C150 10 165 20 155 32 C145 44 165 54 145 50" stroke="url(#connGradDark)" strokeWidth="6" fill="none" strokeLinecap="round"/>
                    <line x1="115" y1="30" x2="130" y2="22" stroke="url(#connGradDark)" strokeWidth="3" strokeLinecap="round"/>
                  </svg>
                </div>
              </div>
            </LogoCardDark>

            {/* C2 - Stacked Letters */}
            <LogoCard label="C2 - Stacked Letters">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <div className="flex flex-col items-center leading-none">
                      <span className="text-4xl font-black bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">A</span>
                      <span className="text-3xl font-black bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent -mt-2">OS</span>
                    </div>
                    <span className="text-xs font-light text-gray-500 tracking-wider uppercase mt-2">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <div className="flex flex-col items-center leading-none">
                      <span className="text-xl font-black bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">A</span>
                      <span className="text-base font-black bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent -mt-1">OS</span>
                    </div>
                    <span className="text-sm font-medium text-gray-700">Agency OS</span>
                  </div>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="C2 - Stacked Letters (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <div className="flex flex-col items-center leading-none">
                      <span className="text-4xl font-black bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">A</span>
                      <span className="text-3xl font-black bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent -mt-2">OS</span>
                    </div>
                    <span className="text-xs font-light text-gray-400 tracking-wider uppercase mt-2">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <div className="flex items-center gap-2">
                    <div className="flex flex-col items-center leading-none">
                      <span className="text-xl font-black bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">A</span>
                      <span className="text-base font-black bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent -mt-1">OS</span>
                    </div>
                    <span className="text-sm font-medium text-gray-300">Agency OS</span>
                  </div>
                </div>
              </div>
            </LogoCardDark>

            {/* C3 - Geometric Integration */}
            <LogoCard label="C3 - Geometric Integration">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <svg width="160" height="50" viewBox="0 0 160 50">
                      <defs>
                        <linearGradient id="geoGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#2563eb" />
                          <stop offset="100%" stopColor="#9333ea" />
                        </linearGradient>
                      </defs>
                      {/* A with integrated diamond */}
                      <path d="M25 45 L40 5 L55 45 M32 32 L48 32" stroke="url(#geoGrad)" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      <rect x="33" y="15" width="14" height="14" transform="rotate(45 40 22)" fill="url(#geoGrad)" opacity="0.3"/>
                      {/* O */}
                      <text x="85" y="40" fill="url(#geoGrad)" fontWeight="800" fontSize="40" fontFamily="system-ui">O</text>
                      {/* S */}
                      <text x="120" y="40" fill="url(#geoGrad)" fontWeight="800" fontSize="40" fontFamily="system-ui">S</text>
                    </svg>
                    <span className="text-xs font-light text-gray-500 tracking-wider uppercase">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 mb-2 block">Nav Size</span>
                  <svg width="90" height="28" viewBox="0 0 160 50">
                    <path d="M25 45 L40 5 L55 45 M32 32 L48 32" stroke="url(#geoGrad)" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                    <rect x="33" y="15" width="14" height="14" transform="rotate(45 40 22)" fill="url(#geoGrad)" opacity="0.3"/>
                    <text x="85" y="40" fill="url(#geoGrad)" fontWeight="800" fontSize="40" fontFamily="system-ui">O</text>
                    <text x="120" y="40" fill="url(#geoGrad)" fontWeight="800" fontSize="40" fontFamily="system-ui">S</text>
                  </svg>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="C3 - Geometric Integration (Dark)">
              <div className="space-y-8">
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Full Size</span>
                  <div className="flex flex-col items-center">
                    <svg width="160" height="50" viewBox="0 0 160 50">
                      <defs>
                        <linearGradient id="geoGradDark" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#3b82f6" />
                          <stop offset="100%" stopColor="#a855f7" />
                        </linearGradient>
                      </defs>
                      <path d="M25 45 L40 5 L55 45 M32 32 L48 32" stroke="url(#geoGradDark)" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      <rect x="33" y="15" width="14" height="14" transform="rotate(45 40 22)" fill="url(#geoGradDark)" opacity="0.3"/>
                      <text x="85" y="40" fill="url(#geoGradDark)" fontWeight="800" fontSize="40" fontFamily="system-ui">O</text>
                      <text x="120" y="40" fill="url(#geoGradDark)" fontWeight="800" fontSize="40" fontFamily="system-ui">S</text>
                    </svg>
                    <span className="text-xs font-light text-gray-400 tracking-wider uppercase">
                      Agency Operating System
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Nav Size</span>
                  <svg width="90" height="28" viewBox="0 0 160 50">
                    <path d="M25 45 L40 5 L55 45 M32 32 L48 32" stroke="url(#geoGradDark)" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                    <rect x="33" y="15" width="14" height="14" transform="rotate(45 40 22)" fill="url(#geoGradDark)" opacity="0.3"/>
                    <text x="85" y="40" fill="url(#geoGradDark)" fontWeight="800" fontSize="40" fontFamily="system-ui">O</text>
                    <text x="120" y="40" fill="url(#geoGradDark)" fontWeight="800" fontSize="40" fontFamily="system-ui">S</text>
                  </svg>
                </div>
              </div>
            </LogoCardDark>
          </div>
        </section>

        {/* OPTION D - Minimal Icon */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800 border-b pb-2">
            Option D - Minimal Icon (Favicon/App Icon)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* D1 - Circle */}
            <LogoCard label="D1 - Circle">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-2xl">A</span>
                  </div>
                  <span className="text-xs text-gray-500">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">A</span>
                  </div>
                  <span className="text-xs text-gray-500">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-xs">A</span>
                  </div>
                  <span className="text-xs text-gray-500">24px</span>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="D1 - Circle (Dark)">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-2xl">A</span>
                  </div>
                  <span className="text-xs text-gray-400">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">A</span>
                  </div>
                  <span className="text-xs text-gray-400">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-xs">A</span>
                  </div>
                  <span className="text-xs text-gray-400">24px</span>
                </div>
              </div>
            </LogoCardDark>

            {/* D2 - Rounded Square */}
            <LogoCard label="D2 - Rounded Square">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-2xl">A</span>
                  </div>
                  <span className="text-xs text-gray-500">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">A</span>
                  </div>
                  <span className="text-xs text-gray-500">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <span className="text-white font-bold text-xs">A</span>
                  </div>
                  <span className="text-xs text-gray-500">24px</span>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="D2 - Rounded Square (Dark)">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-2xl">A</span>
                  </div>
                  <span className="text-xs text-gray-400">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">A</span>
                  </div>
                  <span className="text-xs text-gray-400">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-xs">A</span>
                  </div>
                  <span className="text-xs text-gray-400">24px</span>
                </div>
              </div>
            </LogoCardDark>

            {/* D3 - Hexagon */}
            <LogoCard label="D3 - Hexagon">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <svg width="64" height="64" viewBox="0 0 64 64">
                    <defs>
                      <linearGradient id="iconHexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#2563eb" />
                        <stop offset="100%" stopColor="#9333ea" />
                      </linearGradient>
                    </defs>
                    <path d="M32 4 L58 18 L58 46 L32 60 L6 46 L6 18 Z" fill="url(#iconHexGrad)" />
                    <text x="32" y="40" textAnchor="middle" fill="white" fontWeight="bold" fontSize="24">A</text>
                  </svg>
                  <span className="text-xs text-gray-500">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <svg width="40" height="40" viewBox="0 0 64 64">
                    <path d="M32 4 L58 18 L58 46 L32 60 L6 46 L6 18 Z" fill="url(#iconHexGrad)" />
                    <text x="32" y="40" textAnchor="middle" fill="white" fontWeight="bold" fontSize="24">A</text>
                  </svg>
                  <span className="text-xs text-gray-500">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <svg width="24" height="24" viewBox="0 0 64 64">
                    <path d="M32 4 L58 18 L58 46 L32 60 L6 46 L6 18 Z" fill="url(#iconHexGrad)" />
                    <text x="32" y="40" textAnchor="middle" fill="white" fontWeight="bold" fontSize="24">A</text>
                  </svg>
                  <span className="text-xs text-gray-500">24px</span>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="D3 - Hexagon (Dark)">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <svg width="64" height="64" viewBox="0 0 64 64">
                    <defs>
                      <linearGradient id="iconHexGradDark" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#3b82f6" />
                        <stop offset="100%" stopColor="#a855f7" />
                      </linearGradient>
                    </defs>
                    <path d="M32 4 L58 18 L58 46 L32 60 L6 46 L6 18 Z" fill="url(#iconHexGradDark)" />
                    <text x="32" y="40" textAnchor="middle" fill="white" fontWeight="bold" fontSize="24">A</text>
                  </svg>
                  <span className="text-xs text-gray-400">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <svg width="40" height="40" viewBox="0 0 64 64">
                    <path d="M32 4 L58 18 L58 46 L32 60 L6 46 L6 18 Z" fill="url(#iconHexGradDark)" />
                    <text x="32" y="40" textAnchor="middle" fill="white" fontWeight="bold" fontSize="24">A</text>
                  </svg>
                  <span className="text-xs text-gray-400">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <svg width="24" height="24" viewBox="0 0 64 64">
                    <path d="M32 4 L58 18 L58 46 L32 60 L6 46 L6 18 Z" fill="url(#iconHexGradDark)" />
                    <text x="32" y="40" textAnchor="middle" fill="white" fontWeight="bold" fontSize="24">A</text>
                  </svg>
                  <span className="text-xs text-gray-400">24px</span>
                </div>
              </div>
            </LogoCardDark>

            {/* D4 - Solid (no gradient) */}
            <LogoCard label="D4 - Solid Black">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-2xl bg-black flex items-center justify-center">
                    <span className="text-white font-bold text-2xl">A</span>
                  </div>
                  <span className="text-xs text-gray-500">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-xl bg-black flex items-center justify-center">
                    <span className="text-white font-bold text-lg">A</span>
                  </div>
                  <span className="text-xs text-gray-500">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-black flex items-center justify-center">
                    <span className="text-white font-bold text-xs">A</span>
                  </div>
                  <span className="text-xs text-gray-500">24px</span>
                </div>
              </div>
            </LogoCard>

            <LogoCardDark label="D4 - Solid White">
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-2xl bg-white flex items-center justify-center">
                    <span className="text-black font-bold text-2xl">A</span>
                  </div>
                  <span className="text-xs text-gray-400">64px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center">
                    <span className="text-black font-bold text-lg">A</span>
                  </div>
                  <span className="text-xs text-gray-400">40px</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-white flex items-center justify-center">
                    <span className="text-black font-bold text-xs">A</span>
                  </div>
                  <span className="text-xs text-gray-400">24px</span>
                </div>
              </div>
            </LogoCardDark>
          </div>
        </section>

        {/* Summary */}
        <section className="bg-white rounded-xl p-6 shadow-sm border">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-gray-600">
            <div>
              <h3 className="font-medium text-gray-800 mb-2">Option A</h3>
              <p>Clean wordmark, minimal, professional. Best for text-heavy layouts.</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-800 mb-2">Option B</h3>
              <p>Icon + wordmark combo. Versatile, works at all sizes. Strong brand recognition.</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-800 mb-2">Option C</h3>
              <p>Stylized lettermarks. Creative, memorable. May be harder to read at small sizes.</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-800 mb-2">Option D</h3>
              <p>Minimal icons for favicon/app. Essential for brand consistency across platforms.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function LogoCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border">
      <span className="text-sm font-medium text-gray-700 mb-4 block">{label}</span>
      {children}
    </div>
  );
}

function LogoCardDark({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl p-6 shadow-sm border" style={{ backgroundColor: "#1d1d1f" }}>
      <span className="text-sm font-medium text-gray-300 mb-4 block">{label}</span>
      {children}
    </div>
  );
}
