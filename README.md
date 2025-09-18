# YouTube Subscription Genre Exporter

このリポジトリには、YouTube で登録しているチャンネル一覧を取得し、ジャンル別にまとめたメモ (Markdown) を作成するスクリプトが含まれています。Google の OAuth 認証を利用してユーザー自身のアカウントにアクセスし、YouTube Data API v3 から必要な情報を取得します。

## 必要なもの

1. Python 3.10 以上
2. Google Cloud Console で発行した **デスクトップアプリ用 OAuth クライアント ID**
3. YouTube Data API v3 が有効化されたプロジェクト

## セットアップ

1. 依存パッケージをインストールします。

   ```bash
   pip install -r requirements.txt
   ```

2. Google Cloud Console で OAuth クライアント ID を作成し、ダウンロードした `client_secret_*.json` (ファイル名は任意) をプロジェクト直下に配置します。

## 使い方

下記コマンドを実行すると、ブラウザが起動し Google アカウントでの認証が求められます。初回認証後は `token.json` にリフレッシュトークンが保存され、次回以降は再認証が不要です。

```bash
python youtube_subscriptions.py \
  --client-secret client_secret.json \
  --output subscriptions_memo.md
```

### 主なオプション

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--client-secret` | Google Cloud Console から取得した OAuth クライアントシークレットのパス | (必須) |
| `--token` | OAuth 認証情報を保存するファイルのパス | `token.json` |
| `--output` | 作成される Markdown メモの出力先 | `subscriptions_memo.md` |

## 出力されるメモの形式

スクリプトはチャンネルごとに `topicCategories` を解析し、最初のカテゴリをジャンルとして利用します。ジャンルごとに以下の形式で Markdown ファイルが生成されます。

```markdown
# YouTube Subscriptions by Genre

## Entertainment
- [Channel Title](https://www.youtube.com/channel/XXXXXXXXXXX) — channel description...

## Uncategorized
- [Another Channel](https://www.youtube.com/channel/YYYYYYYYYYY)
```

`topicCategories` が取得できなかったチャンネルは `Uncategorized` に分類されます。必要に応じて出力された Markdown を編集して、自分の好みのメモに整形してください。

## トラブルシューティング

- **`HttpError` が表示される**: API の利用制限に達した、もしくは OAuth の権限が不足している可能性があります。YouTube Data API の割り当てを確認してください。
- **ブラウザが開かない**: `--noauth_local_webserver` オプションを使うとコンソールでコード入力による認証が可能です。必要に応じてスクリプトを修正してください。
- **トピック分類が期待と異なる**: YouTube が提供する `topicCategories` に依存しているため、チャンネルによっては正確なジャンルが得られない場合があります。

## ライセンス

このリポジトリは MIT License で提供されています。
