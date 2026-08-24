$(document).ready(function(){

    // 見出しに入力した時
    $('#post-title').on('input',function(){
        let title = $(this).val();

        // 入力がない時は「見出し」に戻す
        if(title == ''){
            title = '見出し';
        }

        // プレビューの見出しを変更
        $('.preview-title').text(title);
        $('.detail-title').text(title);
    });

    // 内容に入力した時
    $('#post-description').on('input',function(){
        let description = $(this).val();

        // 入力がない時は最初の文章に戻す
        if(description == ''){
            description = '内容がここに表示されます。';
        }

        // 商品詳細ページの内容を変更
        $('.detail-description').text(description);
    });

    // 希望時間に入力した時
    $('#post-time').on('input',function(){
        let time = $(this).val();

        // 入力がない時
        if(time == ''){
            $('.preview-time').text('--分');
            $('.detail-time').text('--分');
        }

        // 入力がある時
        else{
            $('.preview-time').text(time + '分');
            $('.detail-time').text(time + '分');
        }
    });

    // ポイントに入力した時
    $('#post-point').on('input',function(){
        let point = $(this).val();

        // 入力がない時
        if(point == ''){
            $('.preview-point').text('---pt');
            $('.detail-point').text('---pt');
        }

        // 入力がある時
        else{
            $('.preview-point').text(point + 'pt');
            $('.detail-point').text(point + 'pt');
        }
    });

    // 感情をクリックした時
    $('#emotion-options button').on('click',function(){

        // 前に選択した感情を元に戻す
        $('#emotion-options button').removeClass('selected');

        // クリックした感情を選択状態にする
        $(this).addClass('selected');

        // 選択した感情の色を取得
        let color = $(this).css('color');

        // 感情のラインの色を変更
        $('.emotion-color').css('background-color',color);

        // プレビューに感情の色の影を付ける
        $('.home-preview').css('box-shadow','0 5px 15px ' + color);
    });

    // 通話を選択した時
    $('input[name="call"]').on('change',function(){

        // 「有」の時は電話アイコンを表示
        if($(this).val() == 'yes'){
            $('.preview-call').show();
        }
        // 「無」の時は電話アイコンを非表示
        else{
            $('.preview-call').hide();
        }
    });

    // 速達を選択した時
    $('input[name="express"]').on('change',function(){
        // 「有」の時は速達のデザインに変更
        if($(this).val() == 'yes'){
            $('.home-preview').addClass('express');
        }
        // 「無」の時は元に戻す
        else{
            $('.home-preview').removeClass('express');
        }
    });

});