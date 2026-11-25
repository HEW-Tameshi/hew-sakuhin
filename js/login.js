const loginTab = document.getElementById('loginTab');
const registerTab = document.getElementById('registerTab');

const usernameGroup = document.getElementById('usernameGroup');
const regUsername = document.getElementById('regUsername');

const emailForm = document.getElementById('emailForm');
const password = document.getElementById('password');
const togglePassword = document.getElementById('togglePassword');

const submitBtn = document.getElementById('submitBtn');
const forgotPwd = document.getElementById('forgotPwd');

const subTitle = document.getElementById('subTitle');
const navText = document.getElementById('navText');
const toggleModeBtn = document.getElementById('toggleModeBtn');
const googleBtnText = document.getElementById('googleBtnText');

let isLoginMode = true;

// ログイン・新規登録の切り替え
function setAuthMode(loginMode) {
    isLoginMode = loginMode;

    loginTab.classList.toggle('active', isLoginMode);
    registerTab.classList.toggle('active', !isLoginMode);

    loginTab.setAttribute('aria-pressed', String(isLoginMode));
    registerTab.setAttribute('aria-pressed', String(!isLoginMode));

    usernameGroup.classList.toggle('hidden', isLoginMode);
    regUsername.required = !isLoginMode;
    regUsername.disabled = isLoginMode;

    forgotPwd.parentElement.classList.toggle('hidden', !isLoginMode);

    password.value = '';
    password.type = 'password';

    togglePassword.textContent = '表示';
    togglePassword.setAttribute(
        'aria-label',
        'パスワードを表示'
    );

    if (isLoginMode) {
        subTitle.textContent =
            'アカウントにログインしてください。';
        submitBtn.textContent = 'ログイン';
        googleBtnText.textContent = 'Googleで続ける';
        navText.textContent =
            'アカウントをお持ちでない方は';
        toggleModeBtn.textContent = '新規登録';
        password.autocomplete = 'current-password';
    } else {
        subTitle.textContent =
            '新しいアカウントを作成しましょう。';
        submitBtn.textContent = 'アカウント作成';
        googleBtnText.textContent = 'Googleで登録';
        navText.textContent =
            'すでにアカウントをお持ちの方は';
        toggleModeBtn.textContent = 'ログイン';
        password.autocomplete = 'new-password';
    }
}

// ログインタブ
loginTab.addEventListener('click', function () {
    setAuthMode(true);
});

// 新規登録タブ
registerTab.addEventListener('click', function () {
    setAuthMode(false);
});

// 下部の切り替え
toggleModeBtn.addEventListener('click', function () {
    setAuthMode(!isLoginMode);
});

// パスワードの表示・非表示
togglePassword.addEventListener('click', function () {
    if (password.type === 'password') {
        password.type = 'text';
        togglePassword.textContent = '非表示';
        togglePassword.setAttribute(
            'aria-label',
            'パスワードを非表示'
        );
    } else {
        password.type = 'password';
        togglePassword.textContent = '表示';
        togglePassword.setAttribute(
            'aria-label',
            'パスワードを表示'
        );
    }
});

// フォーム送信（プロトタイプ用）
emailForm.addEventListener('submit', function (e) {
    e.preventDefault();
    window.location.href = './index.html';
});

// パスワード再設定（未実装）
forgotPwd.addEventListener('click', function (e) {
    e.preventDefault();
});

// 初期表示
setAuthMode(true);
