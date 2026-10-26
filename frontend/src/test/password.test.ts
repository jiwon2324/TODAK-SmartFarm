import { describe, expect, it } from 'vitest';
import { formatPhone, LOGIN_ID_RE, passwordRules, strength, tempPassword } from '../components/password';

describe('비밀번호·아이디 규칙 (백엔드 PasswordPolicy와 같은 규칙)', () => {
  it('영문·숫자·특수문자 8자 이상, 아이디 미포함이면 통과', () => {
    expect(passwordRules('Tomato#2026a', 'kimfarm').every((r) => r.ok)).toBe(true);
    expect(passwordRules('abcdefgh', 'kimfarm').every((r) => r.ok)).toBe(false);
    expect(passwordRules('kimfarm#2026', 'kimfarm').find((r) => r.key === 'id')?.ok).toBe(false);
    expect(passwordRules('Aaaa#1111x', 'x').find((r) => r.key === 'repeat')?.ok).toBe(false);
  });
  it('강도: 규칙 미충족 1, 충족 2 이상, 12자·대소문자면 4', () => {
    expect(strength('abc', '').score).toBe(1);
    expect(strength('Tomato#2026abcd', '').score).toBe(4);
  });
  it('아이디 형식', () => {
    expect(LOGIN_ID_RE.test('farmer01')).toBe(true);
    expect(LOGIN_ID_RE.test('1farmer')).toBe(false);
    expect(LOGIN_ID_RE.test('ab')).toBe(false);
  });
  it('휴대폰 자동 하이픈', () => {
    expect(formatPhone('01012345678')).toBe('010-1234-5678');
    expect(formatPhone('0101234567')).toBe('010-123-4567');
  });
  it('임시 비밀번호는 규칙을 만족', () => {
    for (let i = 0; i < 20; i++) expect(passwordRules(tempPassword(), 'user').every((r) => r.ok)).toBe(true);
  });
});
