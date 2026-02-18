import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)

# --- 設定 ---
# 開発用データベース（SQLite）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sns.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# シークレットキー（セッション等で使用。本番ではランダムな値に変更すること）
app.config['SECRET_KEY'] = 'dev-secret-key'

db = SQLAlchemy(app)

# --- OpenAIクライアント設定 ---
# APIキーが設定されていない場合はモックモードで動作
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- データベースモデル ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(280), nullable=False) # Xの制限に合わせる
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 表示用に日時をフォーマットするメソッド
    def formatted_time(self):
        return self.timestamp.strftime("%Y/%m/%d %H:%M")

# --- 初期化 ---
with app.app_context():
    db.create_all()

# --- ルーティング ---

@app.route('/')
def index():
    # 最新の投稿順に表示
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/post', methods=['POST'])
def create_post():
    content = request.form.get('content')
    if content and len(content.strip()) > 0:
        new_post = Post(content=content)
        db.session.add(new_post)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    """
    投稿内容を受け取り、AIによる解説や反応を返すAPI
    """
    data = request.json
    post_content = data.get('content')

    if not post_content:
        return jsonify({'error': 'No content provided'}), 400

    # APIキーがない場合のモック動作（開発用）
    if not client:
        import time
        time.sleep(1) # AIの思考時間を演出
        return jsonify({
            'answer': f"【AIモック回答】\nこの投稿「{post_content[:10]}...」は興味深いですね。\nAPIキーを設定すると、GPT-4oが文脈を解析して返答します。"
        })

    try:
        # 実際のOpenAI APIコール
        response = client.chat.completions.create(
            model="gpt-4o-mini", # コストパフォーマンスの良いモデル
            messages=[
                {"role": "system", "content": "あなたはSNSのアシスタントAI（Grokのような存在）です。ユーザーの投稿に対して、機知に富んだコメント、ファクトチェック、あるいは補足情報を短く返してください。"},
                {"role": "user", "content": post_content}
            ]
        )
        answer = response.choices[0].message.content
        return jsonify({'answer': answer})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    