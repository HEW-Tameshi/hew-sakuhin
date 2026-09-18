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
    let selectedColor =  '#b9b5ee';
    let selectedImage =  'images/happy.jpg';
    let selectedEmotion = '';
    

    $('#emotion-options button').mouseenter(function(){

            let id = $(this).attr('id');
            let color = '';
            let image = '';

            // 喜
            if(id == 'joy'){
                color = '#e6a23c';
                image = 'images/happy.jpg';
            }
            else if(id == 'fun'){
                color = '#65a765';
                image = 'images/normal.png';

            }
            else if(id == 'sad'){
                color = '#7772c9';
                image = 'images/sad.png';

            }
            else if(id == 'angry'){
                color = '#d85c5c';
                image = 'images/angry.jpg';

            }

            $(this).css('color', color);
            $('#emotion-color').css('background-color', color);
            $('#home-preview').css('box-shadow', '0 5px 15px ' + color);
            $('#goat').attr('src', image);
        });
        $('#emotion-options button').mouseleave(function(){
            // 選択されていない文字を元の色に戻す
            if(!$(this).hasClass('selected')){
                $(this).css('color', '#333'); 
            }
            // 選択した感情の色に戻す
            $('#emotion-color').css('background-color', selectedColor);
            $('#home-preview').css('box-shadow', '0 5px 15px ' + selectedColor);
            $('#goat').attr('src', selectedImage); 
        });   


    $('#emotion-options button').on('click', function () {

        // すべてのselectedを消す
        $('#emotion-options button').removeClass('selected');

        // すべての文字を元の色に戻す
        $('#emotion-options button').css('color', '#333');

        // 今クリックしたボタンにselectedを付ける
        $(this).addClass('selected');

        // クリックした文字の色を取得
        let id = $(this).attr('id');

        // 選択された感情を保存
        selectedEmotion = id;


        if(id =='joy'){
            selectedColor = '#e6a23c';
            selectedImage = 'images/happy.jpg';
        }
        else if(id =='fun'){
            selectedColor = '#65a765';
            selectedImage = 'images/normal.png';
        }
        else if(id =='sad'){
            selectedColor = '#7772c9';
            selectedImage = 'images/sad.png';
        }
        else if(id =='angry'){
            selectedColor = '#d85c5c';
            selectedImage = 'images/angry.jpg';
        }

        // 選択した文字の色を変更
        $(this).css('color', selectedColor);
        // 感情ラインの色を変更
        $('#emotion-color').css('background-color', selectedColor);
        // カードの影を変更
        $('#home-preview').css('box-shadow', '0 5px 15px ' + selectedColor);
        // 八木の画像を変更
        $('#goat').attr('src', selectedImage);
    });

    // 通話
    $('input[name="call"]').on('change', function () {

        // 有の場合
        if ($(this).val() === 'yes') {

            // 通話の吹き出しを表示
            $('#call-bubble').show();

        // 無の場合
        } else {

            // 通話の吹き出しを非表示
            $('#call-bubble').hide();
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



    $('#post-button').on('click', function () {

        let title = $('#post-title').val();
        let text = $('#post-description').val();
        let category = $('#post-category').val();
        let time = $('#post-time').val();
        let point = $('#post-point').val();
        let call = $('input[name="call"]:checked').val();
        let express = $('input[name="express"]:checked').val();
        let agreement = $('#agreement').is(':checked');

        if (title === '') {
            alert('見出しを入力してください。');
        }
        // 内容が入力されてない
        else if (text === '') {
            alert('内容を入力してください。');
        }
        // 希望時間が入力されていない場合
        else if (time === '') {
            alert('希望時間を入力してください。');
        }
        // ポイントが入力されていない場合
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
        // すべて入力されている場合
        else{
            alert('出品できます。');
            // ホーム画面に移動(index.html)
            window.location.href = 'index.html';
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
