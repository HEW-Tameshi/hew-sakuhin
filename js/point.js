const modal = document.getElementById("purchase-modal");
const modalTitle = document.getElementById("modal-title");
const modalPoint = document.getElementById("modal-point");
const modalPrice = document.getElementById("modal-price");
const currentPoint = document.getElementById("current-point");

const modalClose = document.getElementById("modal-close");
const cancelButton = document.getElementById("cancel-button");
const confirmButton = document.getElementById("confirm-button");
const subscriptionButton = document.getElementById("subscription-button");

let selectedPoint = 0;
let selectedPrice = 0;
let isSubscription = false;

function openModal(point, price, subscription = false) {
  selectedPoint = point;
  selectedPrice = price;
  isSubscription = subscription;

  if (subscription) {
    modalTitle.textContent = "プレミアムプランに登録しますか？";
    modalPoint.textContent = "毎月 700pt";
    modalPrice.textContent = "月額 700円";
  } else {
    modalTitle.textContent = "ポイントを購入しますか？";
    modalPoint.textContent = `${point.toLocaleString()}pt`;
    modalPrice.textContent = `${price.toLocaleString()}円`;
  }

  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
}

document.querySelectorAll(".buy-button").forEach((button) => {
  button.addEventListener("click", () => {
    const point = Number(button.dataset.point);
    const price = Number(button.dataset.price);

    openModal(point, price);
  });
});

subscriptionButton.addEventListener("click", () => {
  openModal(700, 700, true);
});

modalClose.addEventListener("click", closeModal);
cancelButton.addEventListener("click", closeModal);

modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    closeModal();
  }
});

confirmButton.addEventListener("click", () => {
  if (isSubscription) {
    alert("プレミアムプランに登録しました。毎月700ptが付与されます。");
  } else {
    const beforePoint = Number(currentPoint.textContent.replace("pt", ""));
    const afterPoint = beforePoint + selectedPoint;

    currentPoint.textContent = `${afterPoint.toLocaleString()}pt`;
    alert(`${selectedPoint.toLocaleString()}ptを購入しました。`);
  }

  closeModal();
});