import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import signal

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からトークンとチャンネルIDを取得
TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_CHANNEL_IDS = [int(id_str) for id_str in os.getenv('ALLOWED_CHANNEL_IDS', '').split(',') if id_str]

# ロール名
ROLE_NAME = "浮上"

# インテントの設定
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# ボットを初期化
bot = commands.Bot(command_prefix='!', intents=intents)

# グローバル変数
processing = False

@bot.event
async def on_ready():
    print(f'{bot.user.name} がログインしました！')
    # ボットが完全に準備できてからタスクを開始
    await asyncio.sleep(5)  # 5秒待機
    if not restart_task.is_running():
        restart_task.start()

@tasks.loop(minutes=10, count=1)
async def restart_task():
    """10分ごとに再起動"""
    if restart_task.current_loop == 0:
        # 初回実行時はスキップ
        return
    print("10分経過したため再起動します。")
    await bot.close()
    # 終了コード1で終了（GitHub Actionsが再起動）
    os._exit(1)

@bot.event
async def on_message(message):
    global processing
    
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return

    # テキストチャンネル以外では無視
    if not isinstance(message.channel, discord.TextChannel):
        return

    # 許可されたチャンネルIDでない場合は無視
    if message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    # メッセージが空、または🔓を含まない場合は無視
    if not message.content or '🔓' not in message.content:
        await bot.process_commands(message)
        return

    # 既に処理中の場合は無視
    if processing:
        return

    try:
        # 処理中フラグを立てる
        processing = True

        # ロールを取得または作成
        role = discord.utils.get(message.guild.roles, name=ROLE_NAME)
        if role and role in message.author.roles:
            await message.channel.send(
                f"⚠️ {message.author.mention} は既に「{ROLE_NAME}」ロールを持っています。",
                delete_after=10
            )
            return

        if not role:
            role = await message.guild.create_role(
                name=ROLE_NAME,
                mentionable=True,
                reason='浮上用ロールの作成'
            )
            await message.channel.send(
                f"✅ ロール「{ROLE_NAME}」を作成しました。",
                delete_after=10
            )

        # ロールを付与
        await message.author.add_roles(role)
        await message.channel.send(
            f"✅ {message.author.mention} に「{ROLE_NAME}」ロールを付与しました。",
            delete_after=10
        )

    except discord.Forbidden:
        await message.channel.send(
            "❌ 権限が不足しています。",
            delete_after=10
        )
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        await message.channel.send(
            "❌ エラーが発生しました。",
            delete_after=10
        )
    finally:
        # 処理中フラグを下ろす
        processing = False

    # ユーザーのメッセージを削除
    try:
        await message.delete()
    except:
        pass

    # コマンド処理を続行
    await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    """エラー発生時の処理"""
    print(f"エラーが発生しました: {event}")
    import traceback
    traceback.print_exc()
    # エラーが発生したら再起動
    await bot.close()
    os._exit(1)

# メイン処理
def main():
    if not TOKEN:
        print("エラー: .envファイルにDISCORD_TOKENを設定してください")
        return
    if not ALLOWED_CHANNEL_IDS:
        print("エラー: .envファイルにALLOWED_CHANNEL_IDSを設定してください")
        return

    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\nボットを終了します...")
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
        os._exit(1)

if __name__ == "__main__":
    main()