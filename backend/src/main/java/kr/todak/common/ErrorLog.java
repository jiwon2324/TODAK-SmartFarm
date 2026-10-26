package kr.todak.common;

import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * 최근 오류·예외 200건을 메모리에 보관한다 (관리자 '오류 로그' 화면용).
 * 서버를 재시작하면 비워진다. 영구 보관이 필요한 이벤트는 TB_ALERT에 남긴다.
 */
@Component
public class ErrorLog {
    public record Entry(LocalDateTime at, String category, String message) {
    }

    private static final int MAX = 200;
    private final Deque<Entry> entries = new ArrayDeque<>();

    public synchronized void add(String category, String message) {
        entries.addFirst(new Entry(LocalDateTime.now(), category, message));
        while (entries.size() > MAX) {
            entries.removeLast();
        }
    }

    public synchronized List<Entry> recent() {
        return new ArrayList<>(entries);
    }
}
