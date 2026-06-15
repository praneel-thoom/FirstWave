import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CoverageBars from '../CoverageBars';

const mockData = {
  median_seconds_saved: 147,
  pct_within_8min_static: 61.2,
  pct_within_8min_staged: 83.7,
};

describe('CoverageBars', () => {
  it('returns null when data is null', () => {
    const { container } = render(<CoverageBars data={null} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders 8-Minute Coverage heading', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('8-Minute Coverage')).toBeInTheDocument();
  });

  it('renders Without FirstWave label', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('Without FirstWave')).toBeInTheDocument();
  });

  it('renders With FirstWave label', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('With FirstWave')).toBeInTheDocument();
  });

  it('displays static percentage', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('61.2%')).toBeInTheDocument();
  });

  it('displays staged percentage', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('83.7%')).toBeInTheDocument();
  });

  it('renders Median Response Time Saved label', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('Median Response Time Saved')).toBeInTheDocument();
  });

  it('displays formatted seconds saved (2 min 27 sec)', () => {
    render(<CoverageBars data={mockData} />);
    expect(screen.getByText('2 min 27 sec')).toBeInTheDocument();
  });
});
