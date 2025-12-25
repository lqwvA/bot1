import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_TOKEN')

# 許可するチャンネル名のリスト
ALLOWED_CHANNEL_NAMES = ["浮上向け"]  # 必要に応じて変更

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

@bot.event
async def on_ready():
    print(f'{bot.user.name} がログインしました！')
    # 処理中フラグを初期化
    bot.processing = False

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return

    # テキストチャンネル以外では無視
    if not isinstance(message.channel, discord.TextChannel):
        return

    # 許可されたチャンネル名でない場合は無視
    if message.channel.name not in ALLOWED_CHANNEL_NAMES:
        return

    # メッセージが空、または🔓を含まない場合は無視
    if not message.content or '🔓' not in message.content:
        await bot.process_commands(message)
        return

    # 既に処理中の場合は無視
    if hasattr(bot, 'processing') and bot.processing:
        return

    try:
        # 処理中フラグを立てる
        bot.processing = True

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
        bot.processing = False

    # ユーザーのメッセージを削除
    try:
        await message.delete()
    except:
        pass

    # コマンド処理を続行
    await bot.process_commands(message)

# Botを起動
if __name__ == "__main__":

    bot.run(TOKEN)
