$(document).ready(function(){

    // 分析の点数
    let score1 = 95;
    let score2 = 88;
    let score3 = 72;

    // 最初は非表示
    $('#personalityarea').hide();
    $('#titlearea').hide();

    // 包容力のバー
    $('#bar1').animate({
        width:score1 + '%'
    },1000);

    // 共感力のバー
    $('#bar2').animate({
        width:score2 + '%'
    },1200);

    // 論理性のバー
    $('#bar3').animate({
        width:score3 + '%'
    },1400);

    // 点数
    let number1 = 0;
    let number2 = 0;
    let number3 = 0;

    // 点数を増やす
    let timer = setInterval(function(){

        if(number1 < score1){
            number1++;
            $('#score1').text(number1);
        }

        if(number2 < score2){
            number2++;
            $('#score2').text(number2);
        }

        if(number3 < score3){
            number3++;
            $('#score3').text(number3);
        }

        // 全部終わったら止める
        if(number1 == score1 && number2 == score2 && number3 == score3){
            clearInterval(timer);
        }

    },15);

    // ランクを動かす
    $('#rankpoint').animate({
        left:'35%'
    },1500);

    // タイプを表示
    setTimeout(function(){

        $('#personalitytext').text('相手を安心させるタイプ');

        $('#personalityarea').fadeIn();

    },1600);

    // 肩書きを表示
    setTimeout(function(){

        $('#titlename').text('言語化の神');

        $('#titlearea').fadeIn();

    },2200);

    // プロフィールに追加
    $('#profilebutton').click(function(){

        $('#profilebutton').text('追加しました！');

    });

    // 閉じる
    $('#closebutton').click(function(){

        window.location.href = 'index.html';

    });

});