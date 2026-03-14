# としくに耳鼻咽喉科 順番待ちモニター

世田谷経堂としくに耳鼻咽喉科の順番待ちシステムを定期確認し、順位が変わったときにmacOS・iPhoneへ通知するツールです。

## 必要環境

- Python 3.9+
- macOS（通知機能に `osascript` を使用）
- iPhone通知を使う場合: [Bark](https://apps.apple.com/jp/app/bark-customed-notifications/id1403753865) アプリ（無料）

## セットアップ

標準ライブラリのみ使用するため、追加インストール不要です。

### iPhoneへの通知を有効にする場合

1. App Storeで **Bark** をインストール
2. アプリを開くと `https://api.day.app/XXXXXXXX/` の形式のURLが表示される
3. そのURLを `--bark-url` オプションで指定する

## 使い方

```bash
# 基本実行（ブラウザのアドレスバーのURLをそのままコピーして貼り付け）
python3 monitor.py "https://gh-fastlist.com/toshikuni-ent/fastlist/0list.php?time=am&id=XX&day=XX&code=XXXXXXX"

# iPhone通知も有効にする
python3 monitor.py "https://..." --bark-url "https://api.day.app/XXXXXXXX/"

# チェック間隔・強調通知のしきい値も指定
python3 monitor.py "https://..." --interval 60 --alert 5
```

## オプション

| 引数 | 説明 | デフォルト |
|---|---|---|
| `url` | マイページのURL（ブラウザのアドレスバーからコピー） | 必須 |
| `--interval` | チェック間隔（秒） | `60` |
| `--alert` | この人数以下になると強調通知 | `5` |
| `--bark-url` | Bark iPhoneアプリのURL | なし（Mac通知のみ） |

## 動作内容

- 指定間隔ごとにURLへアクセスし、待ち人数を取得
- 人数が変わったタイミングでmacOS通知を送信
- `--alert` で指定した人数以下になると「⚠️ もうすぐ呼ばれます！」と強調通知
- `Ctrl+C` で停止
