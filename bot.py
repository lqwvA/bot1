import os
import discord
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# ボットの設定
TOKEN = os.getenv('DISCORD_TOKEN')
ROLE_NAME = "浮上"  # 付与するロール名

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

    # メッセージが空、または🔓を含まない場合は無視
    if not message.content or '🔓' not in message.content:
        await bot.process_commands(message)
        return

    # 処理中フラグを確認（重複処理防止）
    if bot.processing:
        return

    try:
        # 処理中フラグを設定
        bot.processing = True

        # 既にロールを持っているか確認
        role = get(message.guild.roles, name=ROLE_NAME)
        if role and role in message.author.roles:
            await message.channel.send(
                f"⚠️ {message.author.mention} は既に「{ROLE_NAME}」ロールを持っています。",
                delete_after=10
            )
            return

        # ロールを取得（存在しなければ作成）
        if not role:
            try:
                role = await message.guild.create_role(
                    name=ROLE_NAME,
                    mentionable=True,
                    reason='浮上用ロールの作成'
                )
                await message.channel.send(
                    f"✅ ロール「{ROLE_NAME}」を作成しました。",
                    delete_after=10
                )
            except discord.Forbidden:
                await message.channel.send(
                    "❌ ロールを作成する権限がありません。",
                    delete_after=10
                )
                return

        # メンバーにロールを付与
        try:
            await message.author.add_roles(role)
            await message.channel.send(
                f"✅ {message.author.mention} に「{ROLE_NAME}」ロールを付与しました。",
                delete_after=10
            )
        except discord.Forbidden:
            await message.channel.send(
                "❌ ロールを付与する権限がありません。",
                delete_after=10
            )
    
    finally:
        # 処理中フラグを解除
        bot.processing = False

    # 元のメッセージを削除
    try:
        await message.delete()
    except:
        pass

    # コマンドの処理を続行
    await bot.process_commands(message)

# ボットを実行
if __name__ == "__main__":
    if not TOKEN:
        print("エラー: .envファイルにDISCORD_TOKENを設定してください")
    else:
        bot.run(TOKEN)