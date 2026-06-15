import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import WeatherSelector from '../WeatherSelector';

describe('WeatherSelector', () => {
  it('renders Weather label', () => {
    render(<WeatherSelector value="none" onChange={() => {}} />);
    expect(screen.getByText('Weather')).toBeInTheDocument();
  });

  it('renders all three weather options', () => {
    render(<WeatherSelector value="none" onChange={() => {}} />);
    expect(screen.getByText('Clear')).toBeInTheDocument();
    expect(screen.getByText('Light Rain')).toBeInTheDocument();
    expect(screen.getByText('Heavy Storm')).toBeInTheDocument();
  });

  it('renders 3 radio inputs', () => {
    render(<WeatherSelector value="none" onChange={() => {}} />);
    const radios = screen.getAllByRole('radio');
    expect(radios.length).toBe(3);
  });

  it('has the correct radio checked', () => {
    render(<WeatherSelector value="light" onChange={() => {}} />);
    const radios = screen.getAllByRole('radio');
    // The second radio (light) should be checked
    expect(radios[1]).toBeChecked();
    expect(radios[0]).not.toBeChecked();
    expect(radios[2]).not.toBeChecked();
  });

  it('calls onChange when a different option is selected', () => {
    const handleChange = vi.fn();
    render(<WeatherSelector value="none" onChange={handleChange} />);
    fireEvent.click(screen.getByText('Heavy Storm'));
    expect(handleChange).toHaveBeenCalledWith('heavy');
  });

  it('shows temperature and precipitation for each preset', () => {
    render(<WeatherSelector value="none" onChange={() => {}} />);
    // Clear: 22°C / 0mm
    expect(screen.getByText('22°C / 0mm')).toBeInTheDocument();
    // Light Rain: 10°C / 4mm
    expect(screen.getByText('10°C / 4mm')).toBeInTheDocument();
    // Heavy Storm: 4°C / 12mm
    expect(screen.getByText('4°C / 12mm')).toBeInTheDocument();
  });
});
