
from flask import Flask

app = Flask(__name__)

@app.route('/srs/api/hello/<string:name>', methods=['GET', 'POST'])
def hello(name):
    return 'Hello, ' + name + '!'


if __name__ == '__main__':
    app.run(debug=True)