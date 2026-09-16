import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../static/js/time.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { formatCountdown, formatRemainingMinutes, getScheduleState } = await import(moduleUrl);

const entries = [
  { label: "1교시", start: "08:45", end: "09:35" },
  { label: "2교시", start: "09:45", end: "10:35" },
  { label: "3교시", start: "10:45", end: "11:35" },
  { label: "4교시", start: "12:35", end: "13:25" },
];

function at(hour, minute, second = 0) {
  return new Date(2026, 8, 16, hour, minute, second);
}

test("수업 시작 시 해당 교시를 활성화한다", () => {
  const state = getScheduleState(entries, at(8, 45));
  assert.equal(state.activeIndex, 0);
  assert.equal(state.remaining, 50 * 60);
});

test("수업 종료 시 쉬는 시간으로 전환한다", () => {
  const state = getScheduleState(entries, at(9, 35));
  assert.equal(state.activeIndex, -1);
  assert.equal(state.label, "쉬는시간");
  assert.equal(state.remaining, 10 * 60);
});

test("긴 공백은 점심시간으로 표시한다", () => {
  const state = getScheduleState(entries, at(12, 0));
  assert.equal(state.label, "점심시간");
  assert.equal(formatCountdown(state.remaining), "35:00");
});

test("마지막 수업 후 종료 상태를 표시한다", () => {
  const state = getScheduleState(entries, at(13, 25));
  assert.equal(state.label, "오늘 수업 종료");
  assert.equal(state.remaining, null);
});

test("잔여 시간은 시계 형식이 아닌 분 단위로 표시한다", () => {
  assert.equal(formatRemainingMinutes(18 * 60 + 4), "19분 남음");
  assert.equal(formatRemainingMinutes(42), "1분 미만 남음");
});

test("주말에는 교시를 활성화하지 않는다", () => {
  const state = getScheduleState(entries, new Date(2026, 8, 20, 9, 0));
  assert.equal(state.phase, "weekend");
  assert.equal(state.activeIndex, -1);
  assert.equal(state.remaining, null);
});
