FROM python:3.11-slim

WORKDIR /app

# readline用のシステムライブラリをインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreadline-dev \
    && rm -rf /var/lib/apt/lists/*

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# デフォルトコマンド
CMD ["python", "main.py", "--help"]
