import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Signup from '../pages/auth/Signup';

vi.mock('../api/client', () => ({ get: vi.fn(), post: vi.fn() }));

describe('회원가입 화면', () => {
  it('필수 약관에 동의해야 다음 단계로 갈 수 있다', () => {
    render(<MemoryRouter><Signup /></MemoryRouter>);
    const next = screen.getByRole('button', { name: '다음' });
    expect(next).toBeDisabled();
    fireEvent.click(screen.getByLabelText('이용약관 동의'));
    expect(next).toBeDisabled();
    fireEvent.click(screen.getByLabelText('개인정보 수집·이용 동의'));
    expect(next).toBeEnabled();
    fireEvent.click(next);
    expect(screen.getByLabelText(/아이디/)).toBeInTheDocument();
  });
});
