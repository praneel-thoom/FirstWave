import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MapContainer from '../MapContainer';

function renderWithQuery(ui) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

const mockHeatmapData = {
  type: 'FeatureCollection',
  features: [{
    type: 'Feature',
    properties: { zone: 'B1', normalized_intensity: 0.9 },
    geometry: { type: 'MultiPolygon', coordinates: [[[[-73.9, 40.8], [-73.8, 40.8], [-73.8, 40.9], [-73.9, 40.9], [-73.9, 40.8]]]] },
  }],
};

const mockStagingData = {
  type: 'FeatureCollection',
  features: [{
    type: 'Feature',
    properties: { staging_index: 0, coverage_radius_m: 3500 },
    geometry: { type: 'Point', coordinates: [-73.9196, 40.8448] },
  }],
};

describe('MapContainer', () => {
  it('renders the map container div', () => {
    renderWithQuery(
      <MapContainer
        heatmapData={mockHeatmapData}
        stagingData={mockStagingData}
        layerVisibility={{ heatmap: true, staging: true, coverage: true }}
        selectedZone={null}
        onZoneClick={() => {}}
      />
    );
    expect(screen.getByTestId('map')).toBeInTheDocument();
  });

  it('renders choropleth when heatmap layer is visible', () => {
    renderWithQuery(
      <MapContainer
        heatmapData={mockHeatmapData}
        stagingData={mockStagingData}
        layerVisibility={{ heatmap: true, staging: true, coverage: true }}
        selectedZone={null}
        onZoneClick={() => {}}
      />
    );
    expect(screen.getByTestId('source-zones')).toBeInTheDocument();
  });

  it('hides choropleth when heatmap layer is not visible', () => {
    renderWithQuery(
      <MapContainer
        heatmapData={mockHeatmapData}
        stagingData={mockStagingData}
        layerVisibility={{ heatmap: false, staging: true, coverage: true }}
        selectedZone={null}
        onZoneClick={() => {}}
      />
    );
    expect(screen.queryByTestId('source-zones')).not.toBeInTheDocument();
  });

  it('renders staging pins', () => {
    renderWithQuery(
      <MapContainer
        heatmapData={mockHeatmapData}
        stagingData={mockStagingData}
        layerVisibility={{ heatmap: true, staging: true, coverage: true }}
        selectedZone={null}
        onZoneClick={() => {}}
      />
    );
    expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0);
  });
});
