// GA4(Google 애널리틱스 4) 연동 — 운영 단계의 이용 통계 수집
//  - 측정 ID는 빌드할 때 VITE_GA_MEASUREMENT_ID로 넣는다 (.env의 GA_MEASUREMENT_ID → docker-compose build.args)
//  - ID가 없으면 아무것도 불러오지 않고 모든 함수가 아무 일도 하지 않는다 (개발·시험·스냅샷 데모 기본값)
//  - 개인정보: 아이디·이름·연락처·농장 이름은 보내지 않는다. 역할(ADMIN/FARMER/VIEWER)만 사용자 속성으로 보낸다
//  - 광고 신호·Google 신호는 끈다. 화면 이동(SPA)은 page_view를 직접 보낸다

type Params = Record<string, string | number | boolean | undefined>;
type Gtag = (...args: unknown[]) => void;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: Gtag;
  }
}

const ID_RE = /^G-[A-Z0-9]{4,}$/;

export function measurementId(): string | null {
  const id = (import.meta.env.VITE_GA_MEASUREMENT_ID ?? '').trim();
  return ID_RE.test(id) ? id : null;
}

export const gaEnabled = () => measurementId() !== null;

let started = false;

/** 앱 시작 시 한 번 호출. 측정 ID가 있을 때만 gtag.js를 불러온다 */
export function initAnalytics() {
  const id = measurementId();
  if (!id || started || typeof window === 'undefined') return;
  started = true;
  window.dataLayer = window.dataLayer || [];
  // gtag.js는 arguments 객체 자체를 큐로 읽는다 (배열로 바꾸면 무시됨)
  window.gtag = function gtag() {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer!.push(arguments);
  };
  window.gtag('js', new Date());
  window.gtag('config', id, {
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });
  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(s);
}

/** 화면 이동 기록. 경로의 숫자 ID는 :id로 바꿔 같은 화면끼리 모은다 */
export function trackPage(path: string, title?: string) {
  if (!started || !window.gtag) return;
  const clean = path.replace(/\/\d+(?=\/|$)/g, '/:id');
  window.gtag('event', 'page_view', {
    page_path: clean,
    page_location: window.location.origin + clean,
    page_title: title ?? document.title,
  });
}

/** 기능 사용 이벤트 (이름은 GA4 규칙: 영문 소문자·밑줄, 40자 이내) */
export function track(name: string, params: Params = {}) {
  if (!started || !window.gtag) return;
  window.gtag('event', name, params);
}

/** 로그인한 사용자의 역할만 사용자 속성으로 둔다 (로그아웃하면 지움) */
export function setUserRole(role: string | null) {
  if (!started || !window.gtag) return;
  window.gtag('set', 'user_properties', { user_role: role ?? '(none)' });
}

/** 시험용: 모듈 상태 초기화 */
export function _resetForTest() {
  started = false;
}
