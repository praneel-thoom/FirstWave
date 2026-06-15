import '@testing-library/jest-dom';

// Mock mapbox-gl since it requires WebGL context
vi.mock('mapbox-gl', () => ({
  default: {
    Map: vi.fn(),
    Marker: vi.fn(() => ({ setLngLat: vi.fn().mockReturnThis(), addTo: vi.fn() })),
    NavigationControl: vi.fn(),
    supported: vi.fn(() => true),
  },
  Map: vi.fn(),
  Marker: vi.fn(),
}));

// Mock react-map-gl components
vi.mock('react-map-gl', () => ({
  default: ({ children, ...props }) => <div data-testid="map" {...filterDomProps(props)}>{children}</div>,
  Map: ({ children, ...props }) => <div data-testid="map" {...filterDomProps(props)}>{children}</div>,
  Source: ({ children, ...props }) => <div data-testid={`source-${props.id}`}>{children}</div>,
  Layer: (props) => <div data-testid={`layer-${props.id}`} />,
  Marker: ({ children, longitude, latitude }) => (
    <div data-testid="marker" data-lng={longitude} data-lat={latitude}>{children}</div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({ current: null }),
}));

// Filter out non-DOM props to avoid React warnings
function filterDomProps(props) {
  const { mapboxAccessToken, mapStyle, initialViewState, interactiveLayerIds, onMouseMove, onMouseLeave, ...rest } = props;
  return rest;
}

// Mock Plotly
vi.mock('plotly.js-basic-dist-min', () => ({ default: {} }));
vi.mock('react-plotly.js/factory', () => ({
  default: () => (props) => <div data-testid="plotly-chart" />,
}));

// Mock import.meta.env
if (!import.meta.env.VITE_MAPBOX_TOKEN) {
  import.meta.env.VITE_MAPBOX_TOKEN = 'pk.test_token';
}
if (!import.meta.env.VITE_API_BASE_URL) {
  import.meta.env.VITE_API_BASE_URL = 'http://localhost:8000';
}
