import { WEATHER_PRESETS } from '../../constants';

const options = Object.entries(WEATHER_PRESETS);

export default function WeatherSelector({ value, onChange }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 11, color: '#aaa', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 6 }}>Weather</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {options.map(([key, preset]) => (
          <label key={key} style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
            background: value === key ? '#1a2a4a' : 'transparent',
            borderRadius: 4, cursor: 'pointer', fontSize: 12,
          }}>
            <input
              type="radio"
              name="weather"
              checked={value === key}
              onChange={() => onChange(key)}
              style={{ accentColor: '#42A5F5' }}
            />
            <span style={{ color: value === key ? '#fff' : '#aaa' }}>{preset.label}</span>
            <span style={{ color: '#555', fontSize: 10, marginLeft: 'auto' }}>
              {`${preset.temperature}\u00B0C / ${preset.precipitation}mm`}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
