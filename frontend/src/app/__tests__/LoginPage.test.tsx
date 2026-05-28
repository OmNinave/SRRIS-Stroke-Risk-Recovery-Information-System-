import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import axios from 'axios';
import LoginPage from '../page';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() })
}));

// Mock Axios
vi.mock('axios');

describe('LoginPage Component', () => {
  it('displays error message on failed login', async () => {
    // Setup API failure mock
    (axios.post as any).mockRejectedValueOnce({
      response: { status: 401, data: { detail: "Incorrect username or password" } }
    });

    render(<LoginPage />);

    // Fill form
    fireEvent.change(screen.getByPlaceholderText('e.g., dr_smith'), { target: { value: 'dr_smith' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'wrongpass' } });
    
    // Submit
    fireEvent.click(screen.getByText('Secure Entry'));

    // Assert error is displayed
    await waitFor(() => {
      expect(screen.getByText(/Invalid clinician ID or password/i)).toBeInTheDocument();
    });
  });
});
