# Discord Ticket Bot

Discordサーバー向けのチケット管理Botです。ボタンから問い合わせ用チャンネルを作成し、対応が終わったらチケットを閉じられます。

## 主な機能

- `/ticket-panel` でチケット作成パネルを設置
- ボタン操作でチケットチャンネルを作成
- チケット作成者と指定ロールだけが閲覧できる権限設定
- 同じユーザーによる同一カテゴリ内の重複チケット作成を防止
- チケット内のボタン、または `/ticket-close` でクローズ
- 作成者、指定モデレーターロール、チャンネル管理権限を持つメンバーがクローズ可能
- 再起動後もパネルとクローズボタンが動作する永続View

## 動作環境

- Python 3.10 以上
- discord.py 2.x
- Discord Bot Application

## セットアップ

### 1. リポジトリを取得

```bash
git clone https://github.com/walnut1210/Discord-ticket-bot.git
cd Discord-ticket-bot
```

### 2. 仮想環境を作成（任意）

Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 依存パッケージをインストール

```bash
python -m pip install -r requirements.txt
```

### 4. 環境変数を設定

`.env.example` を参考に、次の環境変数を実行環境へ設定してください。

| 変数 | 内容 |
| --- | --- |
| `DISCORD_TOKEN` | Discord Bot Token |
| `MOD_ROLE_ID` | チケットを閲覧・管理するモデレーターロールのID |
| `TICKET_CATEGORY_ID` | チケットチャンネルを作成するカテゴリのID |

このBotは標準では `.env` ファイルを自動読込しません。ホスティングサービスの環境変数設定、またはOSの環境変数として登録してください。

**Bot TokenをソースコードやGitHubへ登録しないでください。**

### 5. Discord Botの設定

1. Discord Developer PortalでApplicationとBotを作成します。
2. Botを対象サーバーへ招待します。
3. Botに以下の権限を付与します。
   - View Channels
   - Send Messages
   - Read Message History
   - Embed Links
   - Manage Channels
4. サーバーでDeveloper Modeを有効にし、モデレーターロールとチケットカテゴリのIDを取得します。
5. 取得したIDを環境変数へ設定します。

### Privileged Gateway Intents

この実装では、**Privileged Gateway Intentsは不要**です。

- Server Members Intent: 不要
- Message Content Intent: 不要
- Presence Intent: 不要

スラッシュコマンドとボタンのInteractionを利用しているため、メッセージ本文の読み取りやメンバー一覧の取得を行いません。

### 6. 起動

```bash
python bot.py
```

起動後、サーバーで `/ticket-panel` を実行するとパネルを設置できます。設置にはサーバー管理権限が必要です。

## 設定上の注意

- `MOD_ROLE_ID` はチケット対応担当者のロールIDです。
- `TICKET_CATEGORY_ID` はチケットチャンネルを作成するカテゴリIDです。
- Bot自身にチャンネルの作成・削除・閲覧・メッセージ送信権限が必要です。
- チケットを閉じると、チャンネルは5秒後に削除されます。必要な記録は削除前に別途保存してください。
- Discord側の権限設定やサーバー構成によっては、追加の調整が必要になる場合があります。

## ライセンス

このリポジトリには、著作権者の事前許可なく再配布・改変・商用利用を行えない独自ライセンスを適用しています。詳細は [LICENSE](LICENSE) を確認してください。
