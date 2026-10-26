import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge, SimNotice, Stat } from '../components/ui';

describe('ui', () => {
  it('Stat 카드에 라벨과 값을 보여준다', () => {
    render(<Stat label="온도" value="24.1℃" />);
    expect(screen.getByText('온도')).toBeInTheDocument();
    expect(screen.getByText('24.1℃')).toBeInTheDocument();
  });
  it('Badge 렌더', () => {
    render(<Badge tone="green">정상</Badge>);
    expect(screen.getByText('정상')).toBeInTheDocument();
  });
  it('시뮬레이션 안내 문구를 표시한다', () => {
    const { container } = render(<SimNotice />);
    expect(container.textContent).toMatch(/시뮬레이/);
  });
});
