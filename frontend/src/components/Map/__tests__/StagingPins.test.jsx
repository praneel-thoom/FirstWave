import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StagingPins from '../StagingPins';

const mockStagingData = {
  type: 'FeatureCollection',
  ambulance_count: 3,
  features: [
    {
      type: 'Feature',
      properties: { staging_index: 0, coverage_radius_m: 3500, predicted_demand_coverage: 31.2, cluster_zones: ['B1', 'B2'] },
      geometry: { type: 'Point', coordinates: [-73.9196, 40.8448] },
    },
    {
      type: 'Feature',
      properties: { staging_index: 1, coverage_radius_m: 3500, predicted_demand_coverage: 25.0, cluster_zones: ['K3', 'K4'] },
      geometry: { type: 'Point', coordinates: [-73.9075, 40.6929] },
    },
  ],
};

describe('StagingPins', () => {
  it('returns null when data is null', () => {
    const { container } = render(<StagingPins data={null} showPins={true} showCoverage={true} />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null when features is missing', () => {
    const { container } = render(<StagingPins data={{ type: 'FeatureCollection' }} showPins={true} showCoverage={true} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders zone pills and ambulance dots when showPins is true', () => {
    render(<StagingPins data={mockStagingData} showPins={true} showCoverage={false} ambulanceCount={3} />);
    // 2 zone label pills + 3 ambulance dots = 5 markers
    const markers = screen.getAllByTestId('marker');
    expect(markers.length).toBe(5);
  });

  it('does not render markers when showPins is false', () => {
    render(<StagingPins data={mockStagingData} showPins={false} showCoverage={false} />);
    expect(screen.queryAllByTestId('marker').length).toBe(0);
  });

  it('renders coverage circles when showCoverage is true', () => {
    render(<StagingPins data={mockStagingData} showPins={false} showCoverage={true} />);
    expect(screen.getByTestId('source-coverage-circles')).toBeInTheDocument();
    expect(screen.getByTestId('layer-coverage-fill')).toBeInTheDocument();
    expect(screen.getByTestId('layer-coverage-stroke')).toBeInTheDocument();
  });

  it('does not render coverage when showCoverage is false', () => {
    render(<StagingPins data={mockStagingData} showPins={true} showCoverage={false} />);
    expect(screen.queryByTestId('source-coverage-circles')).not.toBeInTheDocument();
  });

  it('renders zone pill labels with allocation counts', () => {
    render(<StagingPins data={mockStagingData} showPins={true} showCoverage={false} ambulanceCount={3} />);
    expect(screen.getByText('Z1')).toBeInTheDocument();
    expect(screen.getByText('Z2')).toBeInTheDocument();
    // 3 ambulances over 2 clusters: highest-demand cluster gets 2, the other 1
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('passes correct coordinates to markers', () => {
    render(<StagingPins data={mockStagingData} showPins={true} showCoverage={false} />);
    const markers = screen.getAllByTestId('marker');
    expect(markers[0]).toHaveAttribute('data-lng', '-73.9196');
    expect(markers[0]).toHaveAttribute('data-lat', '40.8448');
  });
});
