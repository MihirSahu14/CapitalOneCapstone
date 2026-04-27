import { render, screen } from '@testing-library/react';
import App from './App';

test('renders sentinel demo navigation', () => {
  render(<App />);
  expect(screen.getByText(/Sentinel\.AI Local Console/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Past Transactions/i })).toBeInTheDocument();
});
