import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LayerToggle from '../LayerToggle';

describe('LayerToggle', () => {
  const defaultVisibility = { heatmap: true, staging: true, coverage: true, stations: false };

  it('renders Layers label', () => {
    render(<LayerToggle visibility={defaultVisibility} onChange={() => {}} />);
    expect(screen.getByText('Layers')).toBeInTheDocument();
  });

  it('renders 4 checkboxes', () => {
    render(<LayerToggle visibility={defaultVisibility} onChange={() => {}} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(4);
  });

  it('renders layer labels', () => {
    render(<LayerToggle visibility={defaultVisibility} onChange={() => {}} />);
    expect(screen.getByText('Demand Heatmap')).toBeInTheDocument();
    expect(screen.getByText('Staging Pins')).toBeInTheDocument();
    expect(screen.getByText('Coverage Circles')).toBeInTheDocument();
    expect(screen.getByText('EMS Stations')).toBeInTheDocument();
  });

  it('checkboxes reflect visibility state', () => {
    const vis = { heatmap: true, staging: false, coverage: true, stations: false };
    render(<LayerToggle visibility={vis} onChange={() => {}} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).toBeChecked();     // heatmap
    expect(checkboxes[1]).not.toBeChecked();  // staging
    expect(checkboxes[2]).toBeChecked();      // coverage
    expect(checkboxes[3]).not.toBeChecked();  // stations
  });

  it('calls onChange with key and new checked state', () => {
    const handleChange = vi.fn();
    render(<LayerToggle visibility={defaultVisibility} onChange={handleChange} />);
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]); // uncheck heatmap
    expect(handleChange).toHaveBeenCalledWith('heatmap', false);
  });
});
