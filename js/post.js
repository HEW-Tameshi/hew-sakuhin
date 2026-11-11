
// 出品機能（作成途中）
// 入力内容のプレビュー、入力チェック、Flaskへの送信処理を作成
// DB登録後の画面移動はまだ
// ※動作確認はまだしていません


$(document).ready(function () {

    // 見出し
    $('#post-title').on('input', function () {
        let title = $(this).val();
        if (title === '') {
            title = '見出し';
        }
        $('#home-title').text(title);
        $('#detail-title').text(title);
    });


    // 内容
    $('#post-description').on('input', function () {

        let text = $(this).val();

        if (text === '') {
            text = '内容がここに表示されます。';
        }
        $('#detail-text').text(text);
    });

    // 希望時間
    $('#post-time').on('input', function () {

        let time = $(this).val();

        if (time === '') {
            $('#home-time').text('--分');
            $('#detail-time').text('--分');
        } else {
            $('#home-time').text(time + '分');
            $('#detail-time').text(time + '分');
        }
    });


    // POINT
    $('#post-point').on('input', function () {

        let point = $(this).val();

        if (point === '') {
            $('#home-point').text('---pt');
            $('#detail-point').text('---pt');
        } else {
            $('#home-point').text(point + 'pt');
            $('#detail-point').text(point + 'pt');
        }
    });


    // 感情
    let selectedColor = '#b9b5ee';
    let selectedImage = 'images/happy.jpg';
    let selectedEmotion = '';


    $('#emotion-options button').mouseenter(function () {

        let id = $(this).attr('id');
        let color = '';
        let image = '';

        if (id == 'joy') {
            color = '#e6a23c';
            image = 'images/happy.jpg';
        }
        else if (id == 'fun') {
            color = '#65a765';
            image = 'images/normal.png';
        }
        else if (id == 'sad') {
            color = '#7772c9';
            image = 'images/sad.png';
        }
        else if (id == 'angry') {
            color = '#d85c5c';
            image = 'images/angry.jpg';
        }

        $(this).css('color', color);
        $('#emotion-color').css('background-color', color);
        $('#detail-emotion-color').css('background-color', color);
        $('#home-preview').css('box-shadow', '0 5px 15px ' + color);
        $('#detail-preview').css('box-shadow', '0 5px 15px ' + color);
        $('#goat').attr('src', image);
    });


    $('#emotion-options button').mouseleave(function () {

        if (!$(this).hasClass('selected')) {
            $(this).css('color', '#333');
        }

        $('#emotion-color').css('background-color', selectedColor);
        $('#detail-emotion-color').css('background-color', selectedColor);
        $('#home-preview').css('box-shadow', '0 5px 15px ' + selectedColor);
        $('#detail-preview').css('box-shadow', '0 5px 15px ' + selectedColor);
        $('#goat').attr('src', selectedImage);
    });


    $('#emotion-options button').on('click', function () {

        $('#emotion-options button').removeClass('selected');
        $('#emotion-options button').css('color', '#333');

        $(this).addClass('selected');

        let id = $(this).attr('id');
        selectedEmotion = id;

        if (id == 'joy') {
            selectedColor = '#e6a23c';
            selectedImage = 'images/happy.jpg';
        }
        else if (id == 'fun') {
            selectedColor = '#65a765';
            selectedImage = 'images/normal.png';
        }
        else if (id == 'sad') {
            selectedColor = '#7772c9';
            selectedImage = 'images/sad.png';
        }
        else if (id == 'angry') {
            selectedColor = '#d85c5c';
            selectedImage = 'images/angry.jpg';
        }

        $(this).css('color', selectedColor);
        $('#emotion-color').css('background-color', selectedColor);
        $('#detail-emotion-color').css('background-color', selectedColor);
        $('#home-preview').css('box-shadow', '0 5px 15px ' + selectedColor);
        $('#detail-preview').css('box-shadow', '0 5px 15px ' + selectedColor);
        $('#goat').attr('src', selectedImage);
    });


    // 通話
    $('input[name="call"]').on('change', function () {

        $('input[name="call"]').parent().removeClass('selected');
        $(this).parent().addClass('selected');

        if ($(this).val() === 'yes') {
            $('#phone-option').addClass('selected');
            $('#detail-phone-option').addClass('selected');
            $('#call-icon').attr('src', 'images/telefone.png');
            $('#call-bubble').show();
        } else {
            $('#phone-option').removeClass('selected');
            $('#detail-phone-option').removeClass('selected');
            $('#call-icon').attr('src', 'images/chat.png');
            $('#call-bubble').show();
        }
    });


    // 速達
    $('input[name="express"]').on('change', function () {

        $('input[name="express"]').parent().removeClass('selected');
        $(this).parent().addClass('selected');

        if ($(this).val() === 'yes') {
            $('#home-preview').addClass('express');
        } else {
            $('#home-preview').removeClass('express');
        }
    });


    // 出品ボタン
    $('#post-button').on('click', function (event) {

        event.preventDefault();

        let title = $('#post-title').val();
        let text = $('#post-description').val();
        let category = $('#post-category').val();
        let time = $('#post-time').val();
        let point = $('#post-point').val();
        let call = $('input[name="call"]:checked').val();
        let express = $('input[name="express"]:checked').val();
        let agreement = $('#agreement').is(':checked');

        // 入力チェック
        if (title.trim() === '') {
            alert('見出しを入力してください。');
        }
        else if (text.trim() === '') {
            alert('内容を入力してください。');
        }
        else if (time === '') {
            alert('希望時間を入力してください。');
        }
        else if (point === '') {
            alert('ポイントを入力してください。');
        }
        else if (call === undefined) {
            alert('通話の有無を選択してください。');
        }
        else if (express === undefined) {
            alert('速達の有無を選択してください。');
        }
        else if (selectedEmotion === '') {
            alert('感情を選択してください。');
        }
        else if (category === '') {
            alert('カテゴリーを選択してください。');
        }
        else if (agreement === false) {
            alert('注意事項に同意してください。');
        }

        // 入力チェックが完了した場合
        else {
            $.ajax({
                url: '/post',
                type: 'POST',
                data: {
                    title: title,
                    content: text,
                    category: category,
                    time: time,
                    point: point,
                    emotion: selectedEmotion,
                    call: call,
                    express: express
                },

                success: function (response) {
                    alert(response);

                    // TODO: 出品完了画面への移動は今後実装する
                    // TODO: jsonifyについて調べた後、レスポンス処理を変更する
                },

                error: function () {
                    alert('通信エラーが発生しました。');
                }
            });
        }
    });

});


// memo
// val() = inputの値を取得
// text() = 文字を変更
// css() = CSSを変更
// show() = 表示
// hide() = 非表示
// addClass() = classを追加
// removeClass() = classを削除
// this = 今操作している要素
