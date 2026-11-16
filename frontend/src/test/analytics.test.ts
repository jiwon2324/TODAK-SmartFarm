import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { _resetForTest, gaEnabled, initAnalytics, track, trackPage } from '../analytics';

describe('GA4 연동', () => {
  beforeEach(() => {
    _resetForTest();
    delete window.gtag;
    delete window.dataLayer;
    document.head.querySelectorAll('script[src*="googletagmanager"]').forEach((s) => s.remove());
  });
  afterEach(() => vi.unstubAllEnvs());

  it('측정 ID가 없으면 스크립트를 불러오지 않고 이벤트도 보내지 않는다', () => {
    vi.stubEnv('VITE_GA_MEASUREMENT_ID', '');
    initAnalytics();
    track('login');
    expect(gaEnabled()).toBe(false);
    expect(window.dataLayer).toBeUndefined();
    expect(document.querySelector('script[src*="googletagmanager"]')).toBeNull();
  });

  it('형식이 틀린 ID(UA- 등)는 무시한다', () => {
    vi.stubEnv('VITE_GA_MEASUREMENT_ID', 'UA-12345-1');
    initAnalytics();
    expect(gaEnabled()).toBe(false);
    expect(window.gtag).toBeUndefined();
  });

  it('측정 ID가 있으면 gtag.js를 한 번 불러오고 광고 신호를 끈 채 설정한다', () => {
    vi.stubEnv('VITE_GA_MEASUREMENT_ID', 'G-TEST1234');
    initAnalytics();
    initAnalytics();
    expect(document.querySelectorAll('script[src*="googletagmanager.com/gtag/js?id=G-TEST1234"]').length).toBe(1);
    const cfg = (window.dataLayer as IArguments[]).map((a) => Array.from(a)).find((a) => a[0] === 'config');
    expect(cfg?.[1]).toBe('G-TEST1234');
    expect(cfg?.[2]).toMatchObject({ send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false });
  });

  it('page_view는 경로의 숫자 ID를 :id로 바꿔 보낸다', () => {
    vi.stubEnv('VITE_GA_MEASUREMENT_ID', 'G-TEST1234');
    initAnalytics();
    trackPage('/farm/12/history', '제어 이력');
    track('device_control', { device_type: 'FAN', action: 'ON' });
    const ev = (window.dataLayer as IArguments[]).map((a) => Array.from(a)).filter((a) => a[0] === 'event');
    expect(ev[0][1]).toBe('page_view');
    expect(ev[0][2]).toMatchObject({ page_path: '/farm/:id/history', page_title: '제어 이력' });
    expect(ev[1]).toEqual(['event', 'device_control', { device_type: 'FAN', action: 'ON' }]);
  });
});
