import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../static/js/display.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { applyFontScales, normalizeFontScales } = await import(moduleUrl);

test("누락된 글씨 배율은 100%를 사용한다", () => {
  assert.deepEqual(normalizeFontScales({ clock: 125 }), {
    clock: 125,
    status: 100,
    notice: 100,
    meal: 100,
    timetable: 100,
  });
});

test("브라우저 적용 전 글씨 배율을 허용 범위로 제한한다", () => {
  assert.deepEqual(
    normalizeFontScales({ clock: 200, status: 50, notice: "120" }),
    {
      clock: 150,
      status: 75,
      notice: 120,
      meal: 100,
      timetable: 100,
    },
  );
});

test("카드별 CSS 변수에 배율을 적용한다", () => {
  const values = {};
  const root = {
    style: {
      setProperty(name, value) {
        values[name] = value;
      },
    },
  };
  applyFontScales({ clock: 125, meal: 90 }, root);
  assert.equal(values["--font-clock-scale"], "125%");
  assert.equal(values["--font-meal-scale"], "90%");
  assert.equal(values["--font-timetable-scale"], "100%");
});
