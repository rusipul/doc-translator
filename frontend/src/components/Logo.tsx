// T2SEMI company logo component
// Replace with <img src="/logo.png"> if you add the actual logo file to frontend/public/logo.png

const RED = '#E31E24'

export function T2SemiLogo({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const logoFile = '/logo.png'

  // If logo file exists in public/, use it; otherwise render styled text
  // To use actual logo: place file at frontend/public/logo.png
  const heights = { sm: 28, md: 44, lg: 64 }
  const h = heights[size]

  return (
    <img
      src={logoFile}
      alt="T2SEMI"
      height={h}
      style={{ display: 'block', objectFit: 'contain' }}
      onError={e => {
        // Fallback to styled text if image not found
        const el = e.currentTarget
        el.style.display = 'none'
        const fallback = el.nextElementSibling as HTMLElement | null
        if (fallback) fallback.style.display = 'block'
      }}
    />
  )
}

export function T2SemiLogoText({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const fontSizes = { sm: 18, md: 30, lg: 46 }
  return (
    <div style={{
      fontFamily: '"Arial Black", "Franklin Gothic Heavy", Impact, sans-serif',
      fontSize: fontSizes[size],
      fontWeight: 900,
      fontStyle: 'italic',
      color: RED,
      letterSpacing: '-1px',
      lineHeight: 1,
      userSelect: 'none',
    }}>
      T2SEMI<span style={{ fontSize: '0.45em', verticalAlign: 'super', marginLeft: 2, fontStyle: 'normal' }}>✦</span>
    </div>
  )
}

// Combined component: tries image first, falls back to styled text
export default function Logo({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <T2SemiLogo size={size} />
      <div style={{ display: 'none' }}>
        <T2SemiLogoText size={size} />
      </div>
    </div>
  )
}
