
from flask import Flask, request, render_template

# TODO: jsonifyはまだ調べていないため、現在は文字列で返す
# TODO: 今後jsonifyについて調べて、変更するか検討する
# TODO: データベース接続は未実装
# TODO: 感情レタートランザクションへの登録処理は今後実装する

# 出品機能（作成途中）
# 画面表示、入力チェック、出品情報の受け取りまで作成
# DB接続、会員情報取得、出品情報の登録はまだ
# 出品完了画面も未実装
# jsonifyはまだ勉強していないため、文字列で返す
# ※動作確認はまだしていません

app = Flask(__name__, template_folder='..', static_folder='..', static_url_path='')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/post', methods=['GET', 'POST'])
def post():
    if request.method == 'POST':

        # JavaScriptから出品情報を取得する
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', '').strip()
        time = request.form.get('time', '').strip()
        point = request.form.get('point', '').strip()
        emotion = request.form.get('emotion', '').strip()
        call = request.form.get('call', '').strip()
        express = request.form.get('express', '').strip()

        # 必須項目の入力チェック
        if not title:
            return '見出しを入力してください。'
        if not content:
            return '内容を入力してください。'
        if not category:
            return 'カテゴーを選択してください。'
        if not time:
            return '希望時間を入力してください。'
        if not point:
            return 'ポイントを入力してください。'
        if not emotion:
            return '感情を選択してください。'
        if not call:
            return '通話の有無を選択してください。'
        if not express:
            return '速達の有無を選択してください。'
        
        # 文字数チェック（上限は仮設定）
        if len(title) > 50:
            return '見出しは50文字以内で入力してください。'

        if len(content) > 1000:
            return '内容は1000文字以内で入力してください。'

        # 希望時間とポイントの数値チェック
        if not time.isdigit():
            return '希望時間は数字で入力してください。'

        if not point.isdigit():
            return 'ポイントは数字で入力してください。'

        time = int(time)
        point = int(point)

        if time <= 0:
            return '希望時間は1以上で入力してください。'

        if point <= 0:
            return 'ポイントは1以上で入力してください。'

        # 出品情報をまとめる
        post_data = {
            'title': title,
            'content': content,
            'category': category,
            'time': time,
            'point': point,
            'emotion': emotion,
            'call': call,
            'express': express
        }

        print('出品データ：', post_data)

        # TODO: 会員マスタから出品者情報を取得する
        # TODO: 感情レタートランザクションに出品情報を登録する
        # TODO: DB登録の成功・失敗を判定する
        # TODO: 出品完了画面への処理を追加する

        return '出品情報を受け取りました。（DB登録は未実装）'

    else:
        return render_template('post.html')


if __name__ == '__main__':
    app.run(debug=True)
