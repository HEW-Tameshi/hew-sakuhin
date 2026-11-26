const authTitle = document.getElementById('authTitle');
const usernameGroup = document.getElementById('usernameGroup');
const regUsername = document.getElementById('regUsername');
const passwordConfirmGroup = document.getElementById('passwordConfirmGroup');
const passwordConfirm = document.getElementById('passwordConfirm');

const emailForm = document.getElementById('emailForm');
const password = document.getElementById('password');
const togglePassword = document.getElementById('togglePassword');
const eyeClosed = togglePassword.querySelector('.eye-closed');
const eyeOpen = togglePassword.querySelector('.eye-open');

const submitBtn = document.getElementById('submitBtn');
const forgotPwd = document.getElementById('forgotPwd');

const navText = document.getElementById('navText');
const toggleModeBtn = document.getElementById('toggleModeBtn');
const googleBtnText = document.getElementById('googleBtnText');

let isLoginMode = true;

// ログイン・新規登録の切り替え
function setAuthMode(loginMode) {
    isLoginMode = loginMode;

    authTitle.textContent = isLoginMode ? 'ログイン' : '新規登録';
    usernameGroup.classList.toggle('hidden', isLoginMode);
    regUsername.required = !isLoginMode;
    regUsername.disabled = isLoginMode;

    passwordConfirmGroup.classList.toggle('hidden', isLoginMode);
    passwordConfirm.required = !isLoginMode;
    passwordConfirm.disabled = isLoginMode;

    forgotPwd.parentElement.classList.toggle('hidden', !isLoginMode);

    password.value = '';
    passwordConfirm.value = '';
    passwordConfirm.setCustomValidity('');
    password.type = 'password';
    eyeClosed.classList.remove('hidden');
    eyeOpen.classList.add('hidden');
    togglePassword.setAttribute('aria-label', 'パスワードを表示');

    if (isLoginMode) {
        submitBtn.textContent = 'ログイン';
        googleBtnText.textContent = 'Googleで続ける';
        navText.textContent = 'アカウントをお持ちでない方は';
        toggleModeBtn.textContent = '新規登録';
        password.autocomplete = 'current-password';
    } else {
        submitBtn.textContent = 'アカウントを作成';
        googleBtnText.textContent = 'Googleで登録';
        navText.textContent = 'すでにアカウントをお持ちの方は';
        toggleModeBtn.textContent = 'ログイン';
        password.autocomplete = 'new-password';
    }
}

// 下部の切り替え
toggleModeBtn.addEventListener('click', function () {
    setAuthMode(!isLoginMode);
});

// パスワードの表示・非表示
togglePassword.addEventListener('click', function () {
    if (password.type === 'password') {
        password.type = 'text';
        eyeClosed.classList.add('hidden');
        eyeOpen.classList.remove('hidden');
        togglePassword.setAttribute('aria-label', 'パスワードを隠す');
    } else {
        password.type = 'password';
        eyeClosed.classList.remove('hidden');
        eyeOpen.classList.add('hidden');
        togglePassword.setAttribute('aria-label', 'パスワードを表示');
    }
});

passwordConfirm.addEventListener('input', function () {
    passwordConfirm.setCustomValidity('');
});

// フォーム送信（プロトタイプ用）
emailForm.addEventListener('submit', function (e) {
    e.preventDefault();

    if (!isLoginMode && password.value !== passwordConfirm.value) {
        passwordConfirm.setCustomValidity('パスワードが一致しません。');
        passwordConfirm.reportValidity();
        return;
    }

    window.location.href = './index.html';
});

// パスワード再設定（未実装）
forgotPwd.addEventListener('click', function (e) {
    e.preventDefault();
});

// 初期表示
setAuthMode(true);
