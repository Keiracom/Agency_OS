export const metadata = {
  title: 'Elliot',
  description: 'Elliot Status Dashboard',
  manifest: '/manifest.json',
  themeColor: '#1a1a2e',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{margin:0,background:'#1a1a2e',color:'#fff',fontFamily:'system-ui'}}>
        {children}
      </body>
    </html>
  )
}
