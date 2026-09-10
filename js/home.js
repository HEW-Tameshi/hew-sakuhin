$(document).ready(function () {
    
    // 保存された出品情報を取得
    let posts = localStorage.getItem('posts');
    // データがあるとき
    if (posts !== null) {
        // 文字列を配列に戻す
        posts = JSON.parse(posts);
        console.log(posts);
        // 出品データを1つずつ取り出す
        posts.forEach(function(post){

            // 通話アイコン
            let callIcon = '';

            if(post.call === 'yes'){
                callIcon = '<img class="call-icon" src="images/telefone.png" alt="通話">';
            }

            // 速達
            let expressClass = '';

            if(post.express === 'yes'){
                expressClass = ' express';
            }

            // 感情
            let emotionColor = '';
            let goatImage = '';

            // 喜
            if(post.emotion === 'joy'){
                emotionColor = '#e6a23c';
                goatImage = 'images/happy.jpg';
            }
            // 楽
            else if(post.emotion === 'fun'){
                emotionColor = '#65a765';
                goatImage = 'images/normal.png';
            }
            // 悲
            else if(post.emotion === 'sad'){
                emotionColor = '#7772c9';
                goatImage = 'images/sad.png';
            }
            // 怒
            else if(post.emotion === 'angry'){
                emotionColor = '#d85c5c';
                goatImage = 'images/angry.jpg';
            }

            // 出品をホームに表示
            $('#new-letter').prepend(
                '<div class="letter ' + post.emotion + expressClass + '">' +
                    '<div class="emotion-color" style="background-color:' + emotionColor + ';\"></div>' +
                    '<p class="category">日常・雑談</p>' +
                    '<div class="letter-title">' +
                        '<h2>' + post.title + '</h2>' +
                        callIcon +
                    '</div>' +
                    '<p class="description">' + post.description + '</p>' +
                    '<div class="letter-info">' +
                        '<span>' + post.point + 'pt</span>' +
                        '<span>/</span>' +
                        '<span>' + post.time + '分</span>' +
                    '</div>' +
                    '<img class="goat" src="' + goatImage + '" alt="感情">' +
                '</div>'
            );
        });
    }

});



// 指定した出品を削除する方法（Consoleで使用）

// localStorageから出品データを取得して配列に戻す
// let posts = JSON.parse(localStorage.getItem('posts'));

// 指定した出品を削除
// posts.splice(1, 1);

// 削除した後のデータをlocalStorageに保存
// localStorage.setItem('posts', JSON.stringify(posts));


// splice(位置, 削除する数)

// 例
// posts.splice(0, 1); → 0番の出品を削除
// posts.splice(1, 1); → 1番の出品を削除
// posts.splice(2, 1); → 2番の出品を削除

// 配列の番号は0から始まる
// 1つ目 → 0
// 2つ目 → 1
// 3つ目 → 2