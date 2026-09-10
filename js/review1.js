$(document).ready(function(){

    // AIまとめの文章
    const summary =
        '・相談内容を最後まで丁寧に聞いていました\n' +
        '・相手の気持ちに共感する言葉が多く見られました\n' +
        '・落ち着いた雰囲気で会話を進めていました\n' +
        '・相手が安心して話せる対応ができていました';

    // 表示する文字の位置
    let count = 0;
    // AIまとめを少しずつ表示
    const timer = setInterval(function(){
        // 1文字ずつ追加
        $('#summarytext').text(
            $('#summarytext').text() + summary.charAt(count)
        );count++;
        // 全部表示したら終了
        if(count >= summary.length){
            clearInterval(timer);
        }
    },20);


    // 星をクリックした時
    $('.star').click(function(){

        // クリックした星の番号
        let starNumber = $(this).index();
        // 全部の星を元に戻す
        $('.star').text('☆');
        $('.star').removeClass('active');

        // 選択した星まで変更
        $('.star').each(function(index){

            if(index <= starNumber){
                // 星を塗りつぶす
                $(this).text('★');
                // 色を付ける
                $(this).addClass('active');
            }
        });

        // 選択した評価を表示
        $('#ratingtext').text((starNumber + 1) + ' / 5');
    });


    // チップを選択した時
    $('.tipbutton').click(function(){
        // 全部の選択を解除
        $('.tipbutton').removeClass('active');
        // クリックしたボタンを選択
        $(this).addClass('active');
        // data-pointからポイントを取得
        let point = $(this).attr('data-point');
        // 選択したポイントを表示
        $('#point').text(point);
    });


    // 送信ボタン
    // $('#sendbutton').click(function(){
    //     // 次のレビュー画面へ移動
    //     window.location.href = 'review2.html';
    // });

    let pointAfterSending = 0;

    // 「送信」を押したとき
    $('#sendbutton').click(function(){

        // 選択中のチップ
        const tipPoint = Number($('#point').text());

        // 現在の所持ポイント
        const currentPoint = Number(
            $('#userpoint').text().replace(/[^0-9]/g, '')
        );

        pointAfterSending = currentPoint - tipPoint;

        $('#confirmTipPoint').text(tipPoint);
        $('#sendBeforePoint').text(currentPoint + 'pt');
        $('#sendAfterPoint').text(pointAfterSending + 'pt');

        // ポイントが足りるか確認
        if(pointAfterSending < 0){
            $('#sendAfterPoint').text('不足');
            $('#sendConfirmMessage').text(
                'ポイントが不足しています。チップを変更してください。'
            );
            $('#sendConfirmButton').prop('disabled', true);
        } else {
            $('#sendConfirmMessage').text(
                'レビューとチップを相手に送信します。'
            );
            $('#sendConfirmButton').prop('disabled', false);
        }

        $('#sendconfirmmodal').css('display', 'flex');
    });

    // キャンセル
    $('#sendCancelButton, #sendconfirmclose').click(function(){
        $('#sendconfirmmodal').hide();
    });

    // モーダルの黒い背景を押したとき
    $('#sendconfirmmodal').click(function(event){
        if(event.target === this){
            $('#sendconfirmmodal').hide();
        }
    });

    // 送信を確定
    $('#sendConfirmButton').click(function(){

        if(pointAfterSending < 0){
            return;
        }

        $('#userpoint').text(pointAfterSending + 'pt');

        window.location.href = 'review2.html';
    });

        $("#closebutton").click(function(){
            window.location.href = 'index.html';
        });
    });

    // charAt(count) -> pega uma letra da frase.
    // setInterval() -> repete ate terminar o texto.
    // $(this).index() -> descobre qual estrela foi clicada.
    // .each() -> passa por cada estrela.
    // .attr('data-point') -> pega o valor de ponto do botao.
    // .addClass() / .removeClass() -> muda o visual da opcao selecionada.