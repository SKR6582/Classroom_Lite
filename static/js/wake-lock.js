let sentinel = null;

export async function enableWakeLock(onStatus) {
  if (!("wakeLock" in navigator)) {
    onStatus("이 브라우저는 화면 켜짐 유지를 지원하지 않습니다.");
    return;
  }

  const request = async () => {
    if (document.visibilityState !== "visible" || sentinel) return;
    try {
      sentinel = await navigator.wakeLock.request("screen");
      onStatus("");
      sentinel.addEventListener("release", () => {
        sentinel = null;
      });
    } catch {
      onStatus("화면 켜짐 유지가 해제되었습니다. 화면을 한 번 터치하세요.");
    }
  };

  document.addEventListener("visibilitychange", request);
  document.addEventListener("pointerdown", request, { passive: true });
  await request();
}
