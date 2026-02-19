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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sns.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key'

db = SQLAlchemy(app)

# OpenAIクライアント設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- データベースモデル ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(280), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def formatted_time(self):
        return self.timestamp.strftime("%Y/%m/%d %H:%M")

# --- 初期化 ---
with app.app_context():
    db.create_all()

# --- ルーティング ---

@app.route('/')
def index():
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

# 【追加】投稿詳細ページ
@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('detail.html', post=post)

# 【既存】インラインAI解析（一覧ページ用）
@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    data = request.json
    post_content = data.get('content')
    
    if not post_content:
        return jsonify({'error': 'No content'}), 400

    if not client:
        import time
        time.sleep(1)
        return jsonify({'answer': "【AIモック】APIキー未設定のため自動応答です。"})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "SNSの投稿に対し、短く気の利いたコメントや補足を行ってください。"},
                {"role": "user", "content": post_content}
            ]
        )
        return jsonify({'answer': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 【追加】対話型AIチャット（詳細ページ用）
@app.route('/api/chat_with_post', methods=['POST'])
def chat_with_post():
    data = request.json
    post_content = data.get('context') # 投稿本文
    user_question = data.get('prompt') # ユーザーの質問

    if not client:
        import time
        time.sleep(1)
        return jsonify({'answer': f"【AIモック回答】\n質問: {user_question}\nに対する回答です。"})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"あなたは有能なAIアシスタントです。以下の投稿内容を前提コンテキストとして、ユーザーの質問に答えてください。\n\n[対象の投稿]\n{post_content}"},
                {"role": "user", "content": user_question}
            ]
        )
        return jsonify({'answer': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)