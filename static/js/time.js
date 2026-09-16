export function formatTime(date) {
  return [date.getHours(), date.getMinutes(), date.getSeconds()]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function formatDate(date) {
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
  return `${date.getFullYear()}년 ${String(date.getMonth() + 1).padStart(2, "0")}월 ${String(date.getDate()).padStart(2, "0")}일 ${weekdays[date.getDay()]}요일`;
}

function secondsAt(time) {
  const [hour, minute] = time.split(":").map(Number);
  return hour * 3600 + minute * 60;
}

export function getScheduleState(entries, now) {
  if (now.getDay() === 0 || now.getDay() === 6) {
    return {
      phase: "weekend",
      activeIndex: -1,
      nextIndex: -1,
      label: "오늘은 수업이 없습니다",
      remaining: null,
      progress: 0,
    };
  }
  const current = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  const activeIndex = entries.findIndex(
    (entry) => current >= secondsAt(entry.start) && current < secondsAt(entry.end),
  );
  if (activeIndex >= 0) {
    const entry = entries[activeIndex];
    const start = secondsAt(entry.start);
    const end = secondsAt(entry.end);
    return {
      phase: "class",
      activeIndex,
      nextIndex: -1,
      label: entry.label,
      remaining: end - current,
      progress: Math.min(100, Math.max(0, ((current - start) / (end - start)) * 100)),
    };
  }

  const nextIndex = entries.findIndex((entry) => secondsAt(entry.start) > current);
  if (nextIndex >= 0) {
    const remaining = secondsAt(entries[nextIndex].start) - current;
    const previousEnd = nextIndex > 0 ? secondsAt(entries[nextIndex - 1].end) : null;
    const gap = previousEnd == null ? 0 : secondsAt(entries[nextIndex].start) - previousEnd;
    return {
      phase: nextIndex === 0 ? "before" : gap >= 30 * 60 ? "lunch" : "break",
      activeIndex: -1,
      nextIndex,
      label: nextIndex === 0 ? "수업 시작 전" : gap >= 30 * 60 ? "점심시간" : "쉬는시간",
      remaining,
      progress: 0,
    };
  }
  return {
    phase: "finished",
    activeIndex: -1,
    nextIndex: -1,
    label: "오늘 수업 종료",
    remaining: null,
    progress: 0,
  };
}

export function formatCountdown(seconds) {
  if (seconds == null) return "--:--";
  const safe = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

export function formatRemainingMinutes(seconds, suffix = "남음") {
  if (seconds == null) return "";
  if (seconds < 60) return `1분 미만 ${suffix}`;
  return `${Math.ceil(seconds / 60)}분 ${suffix}`;
}
