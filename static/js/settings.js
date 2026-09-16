const DAYS = ["월", "화", "수", "목", "금"];
const form = document.querySelector("#settings-form");
const message = document.querySelector("#form-message");
const noticeInput = form.elements.notice;
let state;
let activeOverrideDate = "";

async function load() {
  const response = await fetch("/api/settings", { cache: "no-store" });
  state = await response.json();
  fillForm();
  renderSlots();
  renderWeek();
  document.querySelector("#override-date").value = localDateKey(new Date());
  activeOverrideDate = document.querySelector("#override-date").value;
  renderOverride();
}

function localDateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function fillForm() {
  fillBasicSettings();
  fillNeisSettings();
  fillHelpSettings();
  fillDisplaySettings();
}

function fillBasicSettings() {
  form.elements.classroom_name.value = state.classroom_name || "";
  noticeInput.value = state.notice || "";
  updateNoticeCount();
  form.elements.help_url.value = state.help_url || "";
  form.elements.timetable_source.value = state.timetable_source || "neis";
}

function updateNoticeCount() {
  document.querySelector("#notice-count").textContent = `${noticeInput.value.length} / 240`;
}

function fillNeisSettings() {
  for (const key of ["office_code", "school_code", "school_name", "school_kind", "grade", "class_name"]) {
    form.elements[key].value = state.neis[key] || "";
  }
  document.querySelector("#key-status").textContent = state.neis.api_key_configured
    ? "API 키가 저장되어 있습니다. 변경할 때만 새 키를 입력하세요."
    : "NEIS에서 발급받은 API 키가 필요합니다.";
}

function fillHelpSettings() {
  const help = document.querySelector("#help-link");
  if (state.help_url) {
    help.href = state.help_url;
    help.hidden = false;
  } else {
    help.removeAttribute("href");
    help.hidden = true;
  }
}

function fillDisplaySettings() {
  const scales = state.display?.font_scales || {};
  document.querySelectorAll("[data-font-scale]").forEach((input) => {
    const key = input.dataset.fontScale;
    input.value = scales[key] ?? 100;
    updateFontScaleOutput(key, input.value);
  });
}

function updateFontScaleOutput(key, value) {
  document.querySelector(`[data-font-scale-output="${key}"]`).textContent = `${value}%`;
}

function renderSlots() {
  const editor = document.querySelector("#slots-editor");
  editor.replaceChildren(
    ...state.slots.map((slot, index) => {
      const row = document.createElement("div");
      row.className = "slot-row";
      row.innerHTML = `
        <input aria-label="${index + 1}교시 이름" data-field="label">
        <input aria-label="${index + 1}교시 시작" data-field="start" type="time">
        <input aria-label="${index + 1}교시 종료" data-field="end" type="time">`;
      for (const field of ["label", "start", "end"]) {
        const input = row.querySelector(`[data-field="${field}"]`);
        input.value = slot[field];
        input.addEventListener("change", () => { state.slots[index][field] = input.value; });
      }
      return row;
    }),
  );
}

function renderWeek() {
  const editor = document.querySelector("#week-editor");
  editor.replaceChildren();
  const corner = document.createElement("span");
  editor.append(corner);
  state.slots.forEach((slot) => {
    const label = document.createElement("span");
    label.className = "week-cell-label";
    label.textContent = slot.label;
    editor.append(label);
  });
  for (const day of DAYS) {
    const label = document.createElement("span");
    label.className = "week-cell-label";
    label.textContent = `${day}요일`;
    editor.append(label);
    for (let index = 0; index < state.slots.length; index += 1) {
      const input = document.createElement("input");
      input.value = state.week_subjects[day]?.[index] || "";
      input.placeholder = "과목";
      input.addEventListener("input", () => {
        state.week_subjects[day][index] = input.value;
      });
      editor.append(input);
    }
  }
  editor.style.gridTemplateColumns = `70px repeat(${state.slots.length}, minmax(105px, 1fr))`;
}

function storeCurrentOverride() {
  const date = activeOverrideDate;
  if (!date) return;
  const values = [...document.querySelectorAll("#override-editor input")].map((input) => input.value.trim());
  if (values.some(Boolean)) state.date_overrides[date] = values;
  else delete state.date_overrides[date];
}

function renderOverride() {
  const date = document.querySelector("#override-date").value;
  const values = state.date_overrides[date] || Array(state.slots.length).fill("");
  const editor = document.querySelector("#override-editor");
  editor.replaceChildren(
    ...state.slots.map((slot, index) => {
      const input = document.createElement("input");
      input.placeholder = `${slot.label} (비우면 자동)`;
      input.value = values[index] || "";
      return input;
    }),
  );
}

document.querySelector("#override-date").addEventListener("change", () => {
  storeCurrentOverride();
  activeOverrideDate = document.querySelector("#override-date").value;
  renderOverride();
});
document.querySelector("#clear-override").addEventListener("click", () => {
  const date = document.querySelector("#override-date").value;
  delete state.date_overrides[date];
  renderOverride();
});

noticeInput.addEventListener("input", updateNoticeCount);

document.querySelectorAll("[data-font-scale]").forEach((input) => {
  input.addEventListener("input", () => {
    updateFontScaleOutput(input.dataset.fontScale, input.value);
  });
});
document.querySelector("#reset-font-scales").addEventListener("click", () => {
  document.querySelectorAll("[data-font-scale]").forEach((input) => {
    input.value = "100";
    updateFontScaleOutput(input.dataset.fontScale, input.value);
  });
});

document.querySelector("#school-search").addEventListener("click", async () => {
  const query = document.querySelector("#school-query").value.trim();
  const results = document.querySelector("#school-results");
  results.textContent = "검색 중…";
  try {
    const response = await fetch("/api/schools/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: query, api_key: form.elements.api_key.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    results.replaceChildren(
      ...(data.schools.length ? data.schools : [{ empty: true }]).map((school) => {
        if (school.empty) {
          const text = document.createElement("p");
          text.className = "muted";
          text.textContent = "검색 결과가 없습니다. 아래 코드를 직접 입력하세요.";
          return text;
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "school-result";
        button.innerHTML = `<strong></strong><small></small>`;
        button.querySelector("strong").textContent = `${school.school_name} · ${school.school_kind}`;
        button.querySelector("small").textContent = `${school.office_name} · ${school.address}`;
        button.addEventListener("click", () => {
          for (const key of ["school_name", "school_kind", "office_code", "school_code"]) {
            form.elements[key].value = school[key];
          }
          results.textContent = `${school.school_name}을(를) 선택했습니다. 교육청 코드와 학교 코드가 자동 입력되었습니다.`;
        });
        return button;
      }),
    );
  } catch (error) {
    results.textContent = error.message || "학교 검색에 실패했습니다.";
  }
});

document.querySelector("#export-settings").addEventListener("click", async () => {
  const includeKey = document.querySelector("#include-api-key").checked;
  try {
    const response = await fetch(`/api/settings/export?include_key=${includeKey ? "1" : "0"}`);
    if (!response.ok) throw new Error("설정을 내보내지 못했습니다.");
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "classroom-tv-lite-settings.json";
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error) {
    message.textContent = error.message;
  }
});

document.querySelector("#import-settings").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  message.textContent = "설정을 가져오는 중…";
  try {
    const imported = JSON.parse(await file.text());
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(imported),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "설정 파일이 올바르지 않습니다.");
    state = data.settings;
    fillForm();
    renderSlots();
    renderWeek();
    activeOverrideDate = document.querySelector("#override-date").value;
    renderOverride();
    message.textContent = "설정을 가져왔습니다. API 키 포함 여부를 확인하세요.";
    message.className = "form-message success";
  } catch (error) {
    message.textContent = error instanceof SyntaxError
      ? "JSON 설정 파일 형식이 올바르지 않습니다."
      : error.message;
    message.className = "form-message";
  } finally {
    event.target.value = "";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  storeCurrentOverride();
  collectBasicSettings();
  collectNeisSettings();
  collectDisplaySettings();
  await saveSettings();
});

function collectBasicSettings() {
  state.classroom_name = form.elements.classroom_name.value;
  state.notice = form.elements.notice.value;
  state.help_url = form.elements.help_url.value;
  state.timetable_source = form.elements.timetable_source.value;
}

function collectNeisSettings() {
  state.neis = {
    api_key: form.elements.api_key.value,
    office_code: form.elements.office_code.value,
    school_code: form.elements.school_code.value,
    school_name: form.elements.school_name.value,
    school_kind: form.elements.school_kind.value,
    grade: form.elements.grade.value,
    class_name: form.elements.class_name.value,
  };
}

function collectDisplaySettings() {
  state.display = { font_scales: {} };
  document.querySelectorAll("[data-font-scale]").forEach((input) => {
    state.display.font_scales[input.dataset.fontScale] = Number(input.value);
  });
}

async function saveSettings() {
  message.textContent = "저장 중…";
  message.className = "form-message";
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "저장하지 못했습니다.");
    message.textContent = "저장했습니다.";
    message.className = "form-message success";
    location.href = "/";
  } catch (error) {
    message.textContent = error.message;
  }
}

load().catch((error) => {
  message.textContent = `설정을 불러오지 못했습니다: ${error.message}`;
});
