import { Badge, Card, PageTitle, Table } from '../../components/ui';

/**
 * SCR-09 수확 판별 (REQ-F-07, 확장 범위). 계획서 9.4에 따라 이번 버전에서는 구현하지 않았다.
 * 가짜 결과를 보여 주지 않고, 무엇이 필요하고 어떻게 동작할지만 안내한다.
 */
export default function Harvest() {
  return (
    <div>
      <PageTitle title="수확 판별" desc="카메라 영상으로 방울토마토 착색도를 계산해 수확 후보를 알려 주는 기능입니다" />
      <Card>
        <Badge tone="amber">확장 기능 · 이번 버전 미구현</Badge>
        <p className="mt-3 text-sm text-slate-700">
          개발 계획서에서 수확 판별(REQ-F-07)은 <b>확장 범위</b>입니다. 판별 정확도를 검증하려면 라벨을 붙인 이미지가 300장 이상 필요하고,
          카메라(CAM-01·02)도 아직 설치되지 않았습니다. 그래서 지금은 결과를 만들어 보여 주지 않으며, 수확은 농가가 직접 판단합니다.
        </p>
      </Card>
      <Card title="구현 계획 (계획서 6장·9.1)" className="mt-4">
        <Table head={['단계', '내용', '필요한 것']}>
          {[
            ['1. 촬영', '구역별 고정 카메라로 하루 2회(10시·14시) 베드 촬영', 'CAM-01(Z1)·CAM-02(Z2), PoE/Wi-Fi'],
            ['2. 품질 검사', '역광·초점 불량 이미지는 제외', '밝기·선명도 기준'],
            ['3. 착색도', 'HSV 변환 → 과실 영역 → 붉은 화소 비율 → 단계 분류', 'Python OpenCV 분석 서비스'],
            ['4. 결과 저장', '이미지 결과·수확 후보를 TB_IMAGE_RESULT에 저장 (API-25, API Key)', '테이블은 이미 있음'],
            ['5. 알림', '수확 후보가 생기면 알림, 이 화면에 사진과 착색도 표시 (API-24)', '-'],
            ['6. 검증', '라벨 300장 이상 검증셋에서 정확도 측정 (목표 80%, 측정 대기)', '라벨링 작업'],
          ].map((r) => <tr key={r[0]}>{r.map((c, i) => <td key={i} className="py-2 pr-3 align-top">{c}</td>)}</tr>)}
        </Table>
      </Card>
    </div>
  );
}
