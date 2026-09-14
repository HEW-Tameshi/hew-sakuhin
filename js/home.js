$(document).ready(function () {
   
    $('#newtab').click(function(){
        // 全部の出品を表示
        $('.letter').show();
        // ボタンの色を変更
        $('#newtab').addClass('active');
        $('#expresstab').removeClass('active');
    });

    // 速達
    $('#expresstab').click(function(){
        $('.letter').hide();
        $('.letter.express').show();
        // ボタンの色を変更
        $('#expresstab').addClass('active');
        $('#newtab').removeClass('active');

    });

    // 出品をクリック
    $(document).on('click', '.letter', function(){

        // 見出し
        let title = $(this).find('h2').text();
        // 内容
        let description = $(this).find('.description').text();
        // カテゴリー
        let category = $(this).find('.category').text();
        // ポイント
        let point = $(this).find('.letter-info span').eq(0).text();
        // 時間
        let time = $(this).find('.letter-info span').eq(2).text();

        // 商品詳細に表示
        $('#modal-title').text(title);
        $('#modal-description').text(description);
        $('#modal-category').text(category);
        $('#modal-point').text(point);
        $('#modal-time').text(time);

        // 感情
        if($(this).hasClass('joy')){
            $('#modalemotion').css('background-color','#e6a23c');
        }
        else if($(this).hasClass('fun')){
            $('#modalemotion').css('background-color','#65a765');
        }
        else if($(this).hasClass('sad')){
            $('#modalemotion').css('background-color','#7772c9');
        }
        else if($(this).hasClass('angry')){
            $('#modalemotion').css('background-color','#d85c5c');
        }

        // 速達
        if($(this).hasClass('express')){
            $('#modalexpress').show();
        }
        else{
            $('#modalexpress').hide();
        }

        // 商品詳細を表示
        $('#detailmodal').fadeIn();
    });

    $('#detailclose').click(function(){
        $('#detailmodal').fadeOut();
    });

});

const detailStep = document.getElementById('detailStep');
const confirmStep = document.getElementById('confirmStep');
const completeStep = document.getElementById('completeStep');

const buybutton = document.getElementById('buybutton');
const cancelBuyBtn = document.getElementById('cancelBuyBtn');
const confirmBuyBtn = document.getElementById('confirmBuyBtn');
const startChatBtn = document.getElementById('startChatBtn');

function showPurchaseStep(step) {
    detailStep.classList.remove('is-active');
    confirmStep.classList.remove('is-active');
    completeStep.classList.remove('is-active');

    step.classList.add('is-active');
}

/* 詳細 → 購入確認 */
buybutton.addEventListener('click', () => {
    const point = document.getElementById('modal-point').textContent;
    document.getElementById('confirmPoint').textContent = point.replace('pt', '');

    showPurchaseStep(confirmStep);
});

/* 購入確認 → 詳細 */
cancelBuyBtn.addEventListener('click', () => {
    showPurchaseStep(detailStep);
});

/* 購入確認 → 購入完了 */
confirmBuyBtn.addEventListener('click', () => {
    showPurchaseStep(completeStep);
});

/* 購入完了 → チャット画面 */
startChatBtn.addEventListener('click', () => {
    location.href = 'chat-room.html';
});