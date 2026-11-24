$(document).ready(function () {

    // 投稿日時の表示
    function formatPostedTime(minutes) {
        if (minutes < 1) {
            return 'たった今';
        }
        else if (minutes < 60) {
            return minutes + '分前';
        }
        else if (minutes < 1440) {
            return Math.floor(minutes / 60) + '時間前';
        }
        else {
            return Math.floor(minutes / 1440) + '日前';
        }
    }

    $('.posted-time').each(function () {
        let minutes = Number($(this).attr('data-minutes-ago'));
        let postedAt = Date.now() - minutes * 60000;
        $(this).attr('data-posted-at', postedAt);
    });

    function updatePostedTimes() {
        $('.posted-time').each(function () {
            let postedAt = Number($(this).attr('data-posted-at'));
            let minutes = Math.max(
                0,
                Math.floor((Date.now() - postedAt) / 60000)
            );
            $(this).text(formatPostedTime(minutes));
        });
    }

    updatePostedTimes();
    setInterval(updatePostedTimes, 60000);

    // チャット・通話の表示
    $('.letter').each(function () {
        let call = $(this).attr('data-call');
        $(this).find('.chat-option').addClass('selected');
        $(this).find('.phone-option')
            .toggleClass('selected', call === 'yes');
    });

    $('#newtab').on('click', function () {
        $('.letter').show();
        $('#newtab').addClass('active');
        $('#expresstab').removeClass('active');
    });

    $('#expresstab').on('click', function () {
        $('.letter').hide();
        $('.letter.express').show();
        $('#expresstab').addClass('active');
        $('#newtab').removeClass('active');
    });

    // 購入ステップを切り替える
    function showPurchaseStep(step) {
        $('.purchase-step').removeClass('is-active');
        $(step).addClass('is-active');
    }

    // 出品カードをクリック
    $(document).on('click', '.letter', function () {
        let title = $(this).find('.letter-title h2').text();
        let description = $(this).find('.description').text();
        let category = $(this).find('.category').text();
        let point = $(this).find('.letter-info span').eq(0).text();
        let time = $(this).find('.letter-info span').eq(2).text();

        $('#modal-title').text(title);
        $('#modal-description').text(description);
        $('#modal-category').text(category);
        $('#modal-point').text(point);
        $('#modal-time').text(time);

        // 感情
        if ($(this).hasClass('joy')) {
            $('#modalemotion').css('background-color', '#e5bc78');
        } else if ($(this).hasClass('fun')) {
            $('#modalemotion').css('background-color', '#91be96');
        } else if ($(this).hasClass('sad')) {
            $('#modalemotion').css('background-color', '#a6a0d4');
        } else if ($(this).hasClass('angry')) {
            $('#modalemotion').css('background-color', '#dfa0a5');
        }

        // 速達
        if ($(this).hasClass('express')) {
            $('#modalexpress').show();
        } else {
            $('#modalexpress').hide();
        }

        // チャット・通話
        $('#modal-chat-icon').addClass('selected');
        if ($(this).attr('data-call') === 'yes') {
            $('#modal-call-icon').addClass('selected');
            $('#modal-call-icon').attr('alt', '通話可能');
        } else {
            $('#modal-call-icon').removeClass('selected');
            $('#modal-call-icon').attr('alt', '通話不可');
        }

        // 新しいカードを開く時は詳細画面に戻す
        showPurchaseStep('#detailStep');
        $('#detailmodal').fadeIn();
    });

    $('#detailclose').on('click', function () {
        $('#detailmodal').fadeOut();
        showPurchaseStep('#detailStep');
    });

    $('#detailmodal').on('click', function (event) {
        if (event.target === this) {
            $(this).fadeOut();
            showPurchaseStep('#detailStep');
        }
    });

    /* 詳細 → 購入確認 */
    $('#buybutton').on('click', function () {
        let point = $('#modal-point').text();
        let pointNumber = parseInt(point.replace('pt', ''), 10);
        let userPoint = parseInt($('#userpoint').text().replace('pt', ''), 10);
        let afterPoint = userPoint - pointNumber;

        if (afterPoint < 0) {
            afterPoint = 0;
        }

        $('#confirmTitle').text($('#modal-title').text());
        $('#confirmPoint').text(pointNumber);
        $('#beforePoint').text(userPoint + 'pt');
        $('#afterPoint').text(afterPoint + 'pt');
        showPurchaseStep('#confirmStep');
    });

    /* 購入確認 → 詳細 */
    $('#cancelBuyBtn').on('click', function () {
        showPurchaseStep('#detailStep');
    });

    /* 購入確認 → 購入完了 */
    $('#confirmBuyBtn').on('click', function () {
        let pointNumber = parseInt($('#confirmPoint').text(), 10);
        let userPoint = parseInt($('#userpoint').text().replace('pt', ''), 10);
        let remainingPoint = Math.max(0, userPoint - pointNumber);

        $('#remainingPoint').text(remainingPoint + 'pt');
        showPurchaseStep('#completeStep');
    });

    /* 購入完了 → チャット画面 */
    $('#startChatBtn').on('click', function () {
        location.href = 'chat-room.html';
    });
});