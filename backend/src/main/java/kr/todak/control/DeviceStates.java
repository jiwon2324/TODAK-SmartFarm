package kr.todak.control;

import java.util.Set;

/** 장치 유형별 활성·비활성 상태. 측창은 열림이 활성, 차광막은 닫힘(차광)이 활성이다. */
public final class DeviceStates {
    private DeviceStates() {
    }

    public static String active(String type) {
        return switch (type) {
            case "VENT" -> "OPEN";
            case "SHADE" -> "CLOSE";
            default -> "ON";
        };
    }

    public static String inactive(String type) {
        return switch (type) {
            case "VENT" -> "CLOSE";
            case "SHADE" -> "OPEN";
            default -> "OFF";
        };
    }

    public static boolean isActive(String type, String state) {
        return active(type).equals(state);
    }

    public static Set<String> allowedActions(String type) {
        return switch (type) {
            case "VENT", "SHADE" -> Set.of("OPEN", "CLOSE");
            default -> Set.of("ON", "OFF");
        };
    }

    /** 사용자가 ON/OFF로 보낸 요청을 유형에 맞는 동작으로 바꾼다 */
    public static String normalize(String type, String action) {
        if (allowedActions(type).contains(action)) {
            return action;
        }
        if ("ON".equals(action)) {
            return active(type);
        }
        if ("OFF".equals(action)) {
            return inactive(type);
        }
        throw new IllegalArgumentException("장치 유형 " + type + "에 허용되지 않는 동작: " + action);
    }
}
