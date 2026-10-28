from flask import Flask, request, render_template

app = Flask(__name__, template_folder='..', static_folder='..', static_url_path='')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/post',methods=['GET','POST'])
def post():
    # request method verifcia quao methodo chegou no servidor
    if request.method == 'POST':
        title = request.form['title']
        return title
    else:
        return render_template('post.html')




















if __name__ == '__main__':
    app.run(debug=True)
