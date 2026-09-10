const form = document.querySelector('#messageForm');
const input = document.querySelector('#messageInput');
const messageList = document.querySelector('#messageList');
const callDialog = document.querySelector('#callDialog');
const toast = document.querySelector('#toast');

function currentTime() {
  return new Intl.DateTimeFormat('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date());
}

function resizeInput() {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 116)}px`;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove('is-visible'), 2600);
}

function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  const row = document.createElement('article');
  row.className = 'message-row message-row--me';

  const content = document.createElement('div');
  const bubble = document.createElement('div');
  const time = document.createElement('time');

  bubble.className = 'bubble bubble--me';
  bubble.textContent = text;
  time.textContent = currentTime();

  content.append(bubble, time);
  row.append(content);
  messageList.append(row);

  input.value = '';
  resizeInput();
  messageList.scrollTo({ top: messageList.scrollHeight, behavior: 'smooth' });
  input.focus();
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage();
});

input.addEventListener('input', resizeInput);
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMessage();
  }
});

document.querySelector('#callButton').addEventListener('click', () => callDialog.showModal());
document.querySelector('#closeDialog').addEventListener('click', () => callDialog.close());
document.querySelector('#cancelCall').addEventListener('click', () => callDialog.close());
document.querySelector('#startCall').addEventListener('click', () => {
  callDialog.close();
  showToast('モックアップのため、通話には接続されません');
});

callDialog.addEventListener('click', (event) => {
  if (event.target === callDialog) callDialog.close();
});
