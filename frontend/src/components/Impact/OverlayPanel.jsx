import { useState, useCallback } from 'react';

const OVERLAY_CONFIG = [
  {
    key: 'equity',
    label: 'Equity (SVI)',
    swatch: '#9333ea',
    tooltip: 'Social Vulnerability Index per zone. Darker = more vulnerable.',
  },
];

const SVI_GRADIENT = 'linear-gradient(to right, rgba(233,213,255,0.55), rgba(192,132,252,0.70), rgba(147,51,234,0.82), rgba(107,33,168,0.90), rgba(76,5,149,0.95))';

const mono = "'DM Mono', 'Space Mono', monospace";

function TogglePill({ config, active, onToggle }) {
  const [hovered, setHovered] = useState(false);

  const handleKeyDown = useCallback((e) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      onToggle(config.key);
    }
  }, [onToggle, config.key]);

  return (
    <div
      role="checkbox"
      aria-checked={active}
      aria-label={`Toggle ${config.label} overlay`}
      tabIndex={0}
      onClick={() => onToggle(config.key)}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        borderRadius: 6,
        border: `1px solid ${active ? 'rgba(147,51,234,0.5)' : 'rgba(255,255,255,0.08)'}`,
        background: active ? 'rgba(147,51,234,0.18)' : 'rgba(255,255,255,0.03)',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        filter: hovered ? 'brightness(1.2)' : 'none',
        outline: 'none',
        userSelect: 'none',
      }}
    >
      {/* Toggle switch */}
      <div style={{
        width: 28,
        height: 14,
        borderRadius: 7,
        background: active ? 'rgba(147,51,234,0.6)' : 'rgba(255,255,255,0.12)',
        position: 'relative',
        transition: 'background 0.15s ease',
        flexShrink: 0,
      }}>
        <div style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: active ? '#c084fc' : 'rgba(255,255,255,0.4)',
          position: 'absolute',
          top: 2,
          left: active ? 16 : 2,
          transition: 'all 0.15s ease',
        }} />
      </div>
      <span style={{
        fontSize: 11,
        fontFamily: mono,
        color: active ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.45)',
        letterSpacing: '0.03em',
        transition: 'color 0.15s ease',
      }}>
        {config.label}
      </span>
    </div>
  );
}

function SviLegend() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{
        fontSize: 9,
        fontFamily: mono,
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.35)',
        letterSpacing: '0.06em',
      }}>
        Vulnerability
      </div>
      <div style={{
        height: 8,
        borderRadius: 4,
        background: SVI_GRADIENT,
      }} />
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 9,
        fontFamily: mono,
        color: 'rgba(255,255,255,0.4)',
      }}>
        <span>Low</span>
        <span>High</span>
      </div>
      <div style={{
        fontSize: 9,
        fontFamily: mono,
        color: 'rgba(255,255,255,0.3)',
        lineHeight: 1.4,
        marginTop: 2,
      }}>
        CDC Social Vulnerability Index. Darker purple = more vulnerable communities.
      </div>
    </div>
  );
}

export default function OverlayPanel({ overlays = {}, toggleOverlay = () => {} }) {
  return (
    <div style={{
      flex: '0 0 200px',
      borderLeft: '1px solid #2a2a4a',
      paddingLeft: 12,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      overflow: 'hidden',
    }}>
      <div style={{
        fontSize: 10,
        fontFamily: mono,
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.35)',
        letterSpacing: '0.08em',
      }}>
        Map Overlays
      </div>

      {OVERLAY_CONFIG.map((cfg) => (
        <TogglePill
          key={cfg.key}
          config={cfg}
          active={overlays[cfg.key]}
          onToggle={toggleOverlay}
        />
      ))}

      {overlays.equity && <SviLegend />}
    </div>
  );
}
