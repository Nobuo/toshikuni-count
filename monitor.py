#!/usr/bin/env python3
"""
としくに耳鼻咽喉科 順番待ちモニター
順位が変わったときだけ通知する
"""

import re
import time
import subprocess
import argparse
import urllib.request
import urllib.parse
from html.parser import HTMLParser


class QueueParser(HTMLParser):
    """赤文字で表示されているテキストを抽出するパーサー"""

    def __init__(self):
        super().__init__()
        self.result = None      # 数字
        self.label = None       # 表示文字列（例: "あと10人", "92番目"）
        self._in_red = False
        self._depth = 0
        self._red_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        style = attrs_dict.get("style", "")
        cls = attrs_dict.get("class", "")

        is_red = (
            "color:red" in style.replace(" ", "")
            or "color: red" in style
            or "red" in cls
            or "strong2-2" in cls
        )

        if is_red:
            self._in_red = True
            self._depth = 1
            self._red_text = []
        elif self._in_red:
            self._depth += 1

    def handle_endtag(self, tag):
        if self._in_red:
            self._depth -= 1
            if self._depth <= 0:
                text = "".join(self._red_text).strip()
                self._try_parse(text)
                self._in_red = False
                self._red_text = []

    def handle_data(self, data):
        if self._in_red:
            self._red_text.append(data)

    def _try_parse(self, text):
        # 「XX番目」形式（「目安」の案内文は除外）
        m = re.search(r"(\d+)\s*番目", text)
        if m and "目安" not in text:
            self.result = int(m.group(1))
            self.label = f"{self.result}番目"
            return
        # 「まであとXX人」形式
        m = re.search(r"まであと\s*(\d+)\s*人", text)
        if m:
            self.result = int(m.group(1))
            self.label = f"あと{self.result}人"
            return
        # 「あとXX人」形式（「目安」の案内文は除外）
        m = re.search(r"あと\s*(\d+)\s*人", text)
        if m and "目安" not in text:
            self.result = int(m.group(1))
            self.label = f"あと{self.result}人"
            return


class QueueClosed(Exception):
    """受付終了を示す例外"""
    pass


def fetch_queue_number(url: str):
    """(数字, 表示ラベル) のタプルを返す。取得失敗時は None を返す。受付終了時は QueueClosed を送出。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # 受付終了チェック
        if "リスト上に見つからないため" in html:
            raise QueueClosed("リスト上に見つからないため、マイページを表示することができません。")
        if "予約を受け付けておりません" in html:
            raise QueueClosed("現在、予約を受け付けておりません。")

        # まず赤文字パーサーで試みる
        parser = QueueParser()
        parser.feed(html)
        if parser.result is not None:
            return (parser.result, parser.label)

        # フォールバック: HTML全体から探す
        # 「strong2-2クラスのspanにあとXX人」形式
        m = re.search(r'class="strong2-2">あと(\d+)人', html)
        if m:
            n = int(m.group(1))
            return (n, f"あと{n}人")
        # 「まであとXX人」形式（タグをまたぐケース対応）
        m = re.search(r"まで(?:<[^>]+>)*あと\s*(\d+)\s*人", html)
        if m:
            n = int(m.group(1))
            return (n, f"あと{n}人")
        # 「XX番目」形式（「目安」の案内文は除外）
        for m in re.finditer(r"(\d+)\s*番目", html):
            context = html[max(0, m.start()-10):m.end()+10]
            if "目安" not in context:
                n = int(m.group(1))
                return (n, f"{n}番目")

    except QueueClosed:
        raise
    except Exception as e:
        print(f"[ERROR] 取得失敗: {e}")

    return None


def notify_mac(title: str, message: str):
    """macOS通知を送る"""
    script = f'display notification "{message}" with title "{title}" sound name "Ping"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def notify_bark(bark_url: str, title: str, message: str):
    """Bark (iPhone) に通知を送る"""
    try:
        encoded_title = urllib.parse.quote(title)
        encoded_message = urllib.parse.quote(message)
        url = f"{bark_url.rstrip('/')}/{encoded_title}/{encoded_message}?sound=minuet"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[WARN] iPhone通知失敗: {e}")


def notify(title: str, message: str, bark_url: str = None):
    """通知を送る（Mac + 必要ならiPhone）"""
    notify_mac(title, message)
    if bark_url:
        notify_bark(bark_url, title, message)
    print(f"[通知] {title}: {message}")


def main():
    parser = argparse.ArgumentParser(description="としくに耳鼻咽喉科 順番待ちモニター")
    parser.add_argument("url", help="マイページURL（ブラウザのアドレスバーからコピー）")
    parser.add_argument("--interval", type=int, default=60, help="チェック間隔(秒) (default: 60)")
    parser.add_argument("--alert", type=int, default=5, help="この人数以下で強調通知 (default: 5)")
    parser.add_argument("--bark-url", default=None, help="Bark iPhoneアプリのURL (例: https://api.day.app/XXXXXXXX/)")
    args = parser.parse_args()

    bark_url = getattr(args, "bark_url", None)

    print(f"モニター開始")
    print(f"  チェック間隔: {args.interval}秒")
    print(f"  {args.alert}人以下で強調通知")
    print(f"  iPhone通知: {'有効 (' + bark_url + ')' if bark_url else '無効'}")
    print("Ctrl+C で停止\n")

    last_number = None

    while True:
        now = time.strftime("%H:%M:%S")
        try:
            result = fetch_queue_number(args.url)
        except QueueClosed as e:
            print(f"[{now}] 受付終了: {e}")
            notify("としくに耳鼻咽喉科", "受付が終了しました。プログラムを終了します。", bark_url)
            return

        if result is None:
            print(f"[{now}] 情報を取得できませんでした")
        else:
            number, label = result
            print(f"[{now}] {label}")

            if number != last_number:
                if number <= args.alert:
                    notify("⚠️ もうすぐ呼ばれます！", f"{label}です", bark_url)
                else:
                    notify("としくに耳鼻咽喉科 順番情報", f"{label}です", bark_url)
                last_number = number

        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n停止しました")
