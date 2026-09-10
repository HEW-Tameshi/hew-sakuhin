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


    // 出品ボタンをクリック
    $('#post-button').on('click', function () {

        // 入力された見出しを取得
        let title = $('#post-title').val();
        // 入力された内容を取得
        let text = $('#post-description').val();
        // 入力された希望時間
        let time = $('#post-time').val();
        //入力されたポイント
        let point = $('#post-point').val();
        // 選択された通話
        let call = $('input[name="call"]:checked').val();
        // そくたつ
        let express = $('input[name="express"]:checked').val();
        // 注意事項
        let agreement = $('#agreement').is(':checked');
        // 見出しが入力されていない場合
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
        else if (agreement === false) {
            alert('注意事項に同意してください。');
        } 
        // すべて入力されている場合
        else{
            let post = {
                title: title,
                description: text,
                time: time,
                point: point,
                call: call,
                express: express,
                emotion: selectedEmotion
            };

            console.log(post);
            // 保存されている出品データを取得
            let posts = localStorage.getItem('posts');
            // まだ出品データがない場合
            if(posts === null){
                // 新しい空の配列を作る
                posts = [];
            }
            // すでに出品データがある場合
            else{
                // localStorageの文字列を配列に戻す
                posts = JSON.parse(posts);
            }
            //新しい出品データを配列に追加
            posts.push(post);
            // 配列を文字列にしてlocalstorageに保存
            localStorage.setItem('posts', JSON.stringify(posts));

            // '' nome pra guardar
            localStorage.setItem('postTitle', title);
            // 内容
            localStorage.setItem('postDescription', text);
            // 希望時間
            localStorage.setItem('postTime', time);
            // ポイント
            localStorage.setItem('postPoint', point);
            // 通話
            localStorage.setItem('postCall', call);
            // 速達
            localStorage.setItem('postExpress', express);
            // 感情
            localStorage.setItem('postEmotion', selectedEmotion);

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
// push() = 配列にデータを追加
// JSON.parse() = 文字列を配列に戻す
// JSON.stringify() = 配列を文字列にする


// 複数の出品を保存する方法

// post = 今入力した出品の情報

// localStorageから今までのpostsを取得
// まだ何もない場合は [] を作る

// JSON.parse()
// localStorageのデータは文字列なので配列に戻す

// push()
// 今のpostを配列に追加する
// 例 [post1, post2] → [post1, post2, post3]

// JSON.stringify()
// 配列をlocalStorageに保存できる文字列にする

// 最後にpostsをlocalStorageに保存

// 流れ
// 今までのpostsを取得
// ↓
// 配列に戻す
// ↓
// 新しいpostを追加
// ↓
// 文字列にする
// ↓
// localStorageに保存