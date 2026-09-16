import {
  formatDate,
  formatRemainingMinutes,
  formatTime,
  getScheduleState,
} from "./time.js";
import { enableWakeLock } from "./wake-lock.js";

const elements = {
  classroom: document.querySelector("#classroom-name"),
  date: document.querySelector("#current-date"),
  clock: document.querySelector("#clock"),
  statusPanel: document.querySelector("#status-panel"),
  period: document.querySelector("#period-label"),
  countdown: document.querySelector("#countdown"),
  periodTime: document.querySelector("#period-time"),
  timetable: document.querySelector("#timetable-list"),
  source: document.querySelector("#timetable-source"),
  mealTitle: document.querySelector("#meal-title"),
  mealList: document.querySelector("#meal-list"),
  mealMessage: document.querySelector("#meal-message"),
  notice: document.querySelector("#notice-text"),
  wakeStatus: document.querySelector("#wake-status"),
  notionGuide: document.querySelector("#notion-guide"),
  notionQr: document.querySelector("#notion-qr"),
};

let entries = [];
let loadedDate = localDateKey(new Date());

function localDateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function renderTimetable(timetable) {
  entries = timetable.entries || [];
  elements.source.textContent = {
    neis: "NEIS 자동",
    override: "오늘 수동 보정",
    manual: "기본 시간표",
  }[timetable.source] || "";
  elements.timetable.replaceChildren(
    ...entries.map((entry, index) => {
      const item = document.createElement("li");
      item.className = "timetable-item";
      item.dataset.index = String(index);
      item.innerHTML = `
        <span class="period-name"></span>
        <strong class="subject"></strong>
        <span class="period-meta">
          <span class="period-time"></span>
          <strong class="row-remaining"></strong>
        </span>
        <span class="progress"><span></span></span>`;
      item.querySelector(".period-name").textContent = entry.label;
      item.querySelector(".subject").textContent = entry.subject || "—";
      item.querySelector(".period-time").textContent = `${entry.start} – ${entry.end}`;
      return item;
    }),
  );
  elements.timetable.style.gridTemplateRows = `repeat(${Math.max(entries.length, 1)}, 1fr)`;
}

function renderFooter(helpUrl) {
  if (!helpUrl) {
    elements.notionGuide.hidden = true;
    elements.notionGuide.removeAttribute("href");
    elements.notionQr.removeAttribute("src");
    return;
  }
  let version = 0;
  for (const character of helpUrl) {
    version = ((version << 5) - version + character.charCodeAt(0)) | 0;
  }
  elements.notionGuide.href = helpUrl;
  elements.notionQr.src = `/api/notion-qr?v=${Math.abs(version)}`;
  elements.notionGuide.hidden = false;
}

async function loadDashboard(refresh = false) {
  const suffix = `?date=${loadedDate}${refresh ? "&refresh=1" : ""}`;
  const response = await fetch(`/api/dashboard${suffix}`, { cache: "no-store" });
  if (response.status === 428) {
    location.href = "/setup";
    return;
  }
  if (!response.ok) throw new Error("대시보드 설정을 불러오지 못했습니다.");
  const data = await response.json();
  elements.classroom.textContent = data.classroom_name || "교실";
  elements.notice.textContent = data.notice || "등록된 공지가 없습니다.";
  renderTimetable(data.timetable);
  renderFooter(data.help_url);
}

async function loadMeal(refresh = false) {
  elements.mealMessage.textContent = "";
  const suffix = `?date=${loadedDate}${refresh ? "&refresh=1" : ""}`;
  try {
    const response = await fetch(`/api/meals${suffix}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "급식 정보를 불러오지 못했습니다.");
    const mealDate = new Date(`${data.date}T12:00:00`);
    const isToday = data.date === loadedDate;
    elements.mealTitle.textContent = isToday
      ? "오늘의 점심"
      : `${mealDate.getMonth() + 1}/${mealDate.getDate()} 다음 급식`;
    const items = data.items || [];
    elements.mealList.replaceChildren(
      ...(items.length ? items : ["급식 정보가 없습니다."]).map((text) => {
        const item = document.createElement("li");
        item.textContent = text;
        if (!items.length) item.className = "muted";
        return item;
      }),
    );
    elements.mealMessage.textContent = data.warning || "";
  } catch (error) {
    elements.mealList.innerHTML = '<li class="muted">급식 정보를 불러오지 못했습니다.</li>';
    elements.mealMessage.textContent = error.message;
  }
}

function renderClock(now) {
  elements.clock.textContent = formatTime(now);
  elements.date.textContent = formatDate(now);
}

function renderScheduleStatus(state) {
  elements.statusPanel.classList.toggle("is-active", state.phase === "class");
  if (state.phase === "class") {
    const entry = entries[state.activeIndex];
    elements.period.textContent = `${entry.label} · ${entry.subject || "수업"}`;
    elements.countdown.textContent = formatRemainingMinutes(state.remaining);
    elements.periodTime.textContent = `${entry.start} – ${entry.end}`;
    return;
  }
  elements.period.textContent = state.label;
  if (state.phase === "finished") {
    elements.countdown.textContent = "일과를 마쳤습니다";
    elements.periodTime.textContent = "";
    return;
  }
  if (state.phase === "weekend") {
    elements.countdown.textContent = "편안한 주말 보내세요";
    elements.periodTime.textContent = "";
    return;
  }
  const next = entries[state.nextIndex];
  const suffix = state.phase === "before" ? "후 시작" : "남음";
  elements.countdown.textContent = formatRemainingMinutes(state.remaining, suffix);
  elements.periodTime.textContent = next ? `다음 ${next.label} · ${next.start} 시작` : "";
}

function updateTimetableState(state) {
  document.querySelectorAll(".timetable-item").forEach((item, index) => {
    const active = index === state.activeIndex;
    item.classList.toggle("active", active);
    item.querySelector(".progress > span").style.width = active ? `${state.progress}%` : "0";
    item.querySelector(".row-remaining").textContent = active
      ? formatRemainingMinutes(state.remaining)
      : "";
  });
}

function tick() {
  const now = new Date();
  const dateKey = localDateKey(now);
  if (dateKey !== loadedDate) {
    loadedDate = dateKey;
    loadDashboard().catch(console.error);
    loadMeal().catch(console.error);
  }
  renderClock(now);
  const state = getScheduleState(entries, now);
  renderScheduleStatus(state);
  updateTimetableState(state);
}

document.querySelector("#meal-refresh").addEventListener("click", () => loadMeal(true));
document.querySelector("#timetable-refresh").addEventListener("click", () => loadDashboard(true));
enableWakeLock((message) => {
  elements.wakeStatus.textContent = message;
  elements.wakeStatus.hidden = !message;
});

Promise.all([loadDashboard(), loadMeal()])
  .catch((error) => {
    elements.mealMessage.textContent = error.message;
  })
  .finally(tick);
setInterval(tick, 1000);
