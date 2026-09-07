$(document).ready(function () {

    // 見出し
    // inputされた時に実行
    $('#post-title').on('input', function () {

        // this = 今入力しているpost-title
        // val() = 入力された値を取得
        let title = $(this).val();

        // 入力がない場合
        if (title === '') {
            title = '見出し';
        }

        // text() = 表示する文字を変更
        $('#home-title').text(title);
        $('#detail-title').text(title);
    });


    // 内容
    $('#post-description').on('input', function () {

        // 入力された内容を取得
        let text = $(this).val();

        // 入力がない場合
        if (text === '') {
            text = '内容がここに表示されます。';
        }

        // 商品詳細の内容を変更
        $('#detail-text').text(text);
    });


    // 希望時間
    $('#post-time').on('input', function () {

        // 入力された数字を取得
        let time = $(this).val();

        // 入力がない場合
        if (time === '') {
            $('#home-time').text('--分');
            $('#detail-time').text('--分');
        // 入力がある場合
        } else {
            $('#home-time').text(time + '分');
            $('#detail-time').text(time + '分');
        }
    });


    // POINT
    $('#post-point').on('input', function () {

        // 入力されたポイントを取得
        let point = $(this).val();

        // 入力がない場合
        if (point === '') {
            $('#home-point').text('---pt');
            $('#detail-point').text('---pt');
        // 入力がある場合
        } else {
            $('#home-point').text(point + 'pt');
            $('#detail-point').text(point + 'pt');
        }
    });

    // 感情
    // 喜・楽・悲・怒のどれかをクリックした時
    let selectedColor =  '#b9b5ee';
    let selectedImage =  'images/happy.png';

    $('#emotion-options button').mouseenter(function(){

            let id = $(this).attr('id');
            let color = '';
            let image = '';

            // 喜
            if(id == 'joy'){
                color = '#e6a23c';
                image = 'images/happy.png';
            }
            else if(id == 'fun'){
                color = '#65a765';
                image = 'images/happy.png';

            }
            else if(id == 'sad'){
                color = '#7772c9';
                image = 'images/happy.png';

            }
            else if(id == 'angry'){
                color = '#d85c5c';
                image = 'images/angry.png';

            }

            $(this).css('color', color);
            $('#emotion-color').css('background-color', color);
            $('#home-preview').css('box-shadow', '0 5px 15px ' + color);
            $('#goat').attr('src', image);
        });

    $('#emotion-options button').on('click', function () {

        // すべてのselectedを消す
        $('#emotion-options button').removeClass('selected');

        // 今クリックしたボタンにselectedを付ける
        $(this).addClass('selected');

        // クリックした文字の色を取得
        let color = $(this).css('color');

        // 感情ラインの色を変更
        $('#emotion-color').css('background-color', color);

        // カードの後ろに同じ色の影を付ける
        $('#home-preview').css('box-shadow', '0 5px 15px ' + color);
    });


    // 通話
    // 有・無を変更した時
    $('input[name="call"]').on('change', function () {
        // 有の場合
        if ($(this).val() === 'yes') {
            // 電話アイコンを表示
            $('#call-icon').show();
        // 無の場合
        } else {
            // 電話アイコンを非表示
            $('#call-icon').hide();
        }
    });


    // 速達
    // 有・無を変更した時
    $('input[name="express"]').on('change', function () {
        // 有の場合
        if ($(this).val() === 'yes') {
            // expressというclassを追加
            // CSSの #home-preview.express が使われる
            $('#home-preview').addClass('express');
        // 無の場合
        } else {
            // expressを消して元に戻す
            $('#home-preview').removeClass('express');
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