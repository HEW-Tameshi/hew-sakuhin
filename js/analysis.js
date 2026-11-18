document.addEventListener("DOMContentLoaded", () => {
  // 1. プログレスバーのアニメーション
  const progressBars = document.querySelectorAll(".progress-fill");
  setTimeout(() => {
    progressBars.forEach((bar) => {
      const targetWidth = bar.getAttribute("data-width");
      bar.style.width = targetWidth;
    });
  }, 150);

  // 2. スコア数値のカウントアップアニメーション
  const scoreNumbers = document.querySelectorAll(".score-num");
  scoreNumbers.forEach((numEl) => {
    const target = parseInt(numEl.getAttribute("data-target"), 10);
    let current = 0;
    const step = Math.ceil(target / 25);

    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      numEl.textContent = current;
    }, 25);
  });

  // 3. 「プロフィールに肩書きを追加」ボタンの処理
  const applyProfileBtn = document.getElementById("applyProfileBtn");
  const toast = document.getElementById("toast");

  applyProfileBtn.addEventListener("click", () => {
    if (applyProfileBtn.classList.contains("applied")) return;

    applyProfileBtn.textContent = "プロフィールに設定済み ✓";
    applyProfileBtn.classList.add("applied");

    // トースト通知を表示
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 2500);
  });

  // 4. 過去の会話分析モーダルの開閉処理
  const historyItems = document.querySelectorAll(".history-item");
  const modal = document.getElementById("historyModal");
  const closeModalBtn = document.getElementById("closeModalBtn");

  const modalDate = document.getElementById("modalDate");
  const modalTitle = document.getElementById("modalTitle");
  const modalEval = document.getElementById("modalEval");
  const modalSummary = document.getElementById("modalSummary");

  historyItems.forEach((item) => {
    item.addEventListener("click", () => {
      modalDate.textContent = item.getAttribute("data-date");
      modalTitle.textContent = item.getAttribute("data-title");
      modalEval.textContent = item.getAttribute("data-eval");
      modalSummary.textContent = item.getAttribute("data-summary");

      modal.classList.add("open");
    });
  });

  closeModalBtn.addEventListener("click", () => {
    modal.classList.remove("open");
  });

  // モーダル背景クリックで閉じる
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.remove("open");
    }
  });

  // 5. 戻るボタンの挙動（履歴があれば戻る）
  const backBtn = document.getElementById("backBtn");
  backBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (window.history.length > 1) {
      window.history.back();
    } else {
      alert("設定画面へ戻ります");
    }
  });
});
