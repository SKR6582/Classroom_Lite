import { formatCountdown, formatDate, formatTime, getScheduleState } from "./time.js";
import { enableWakeLock } from "./wake-lock.js";

const elements = {
  classroom: document.querySelector("#classroom-name"),
  date: document.querySelector("#current-date"),
  clock: document.querySelector("#clock"),
  period: document.querySelector("#period-label"),
  countdown: document.querySelector("#countdown"),
  timetable: document.querySelector("#timetable-list"),
  source: document.querySelector("#timetable-source"),
  mealTitle: document.querySelector("#meal-title"),
  mealList: document.querySelector("#meal-list"),
  mealMessage: document.querySelector("#meal-message"),
  notice: document.querySelector("#notice-text"),
  wakeStatus: document.querySelector("#wake-status"),
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
        <span class="period-time"></span>
        <span class="progress"><span></span></span>`;
      item.querySelector(".period-name").textContent = entry.label;
      item.querySelector(".subject").textContent = entry.subject || "—";
      item.querySelector(".period-time").textContent = `${entry.start} – ${entry.end}`;
      return item;
    }),
  );
  elements.timetable.style.gridTemplateRows = `repeat(${Math.max(entries.length, 1)}, 1fr)`;
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
    elements.mealMessage.textContent = [data.warning, data.calories].filter(Boolean).join(" · ");
  } catch (error) {
    elements.mealList.innerHTML = '<li class="muted">급식 정보를 불러오지 못했습니다.</li>';
    elements.mealMessage.textContent = error.message;
  }
}

function tick() {
  const now = new Date();
  const dateKey = localDateKey(now);
  if (dateKey !== loadedDate) {
    loadedDate = dateKey;
    loadDashboard().catch(console.error);
    loadMeal().catch(console.error);
  }
  elements.clock.textContent = formatTime(now);
  elements.date.textContent = formatDate(now);
  const state = getScheduleState(entries, now);
  elements.period.textContent = state.label;
  elements.countdown.textContent = formatCountdown(state.remaining);
  document.querySelectorAll(".timetable-item").forEach((item, index) => {
    const active = index === state.activeIndex;
    item.classList.toggle("active", active);
    item.querySelector(".progress > span").style.width = active ? `${state.progress}%` : "0";
  });
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
