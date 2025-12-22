import os
import discord
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# ボットの設定
TOKEN = os.getenv('DISCORD_TOKEN')
ROLE_NAME = "浮上"  # 付与するロール名を「浮上」に変更

# インテンスの設定
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

# ボットを初期化
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} がログインしました！')
    await bot.change_presence(activity=discord.Game(name=f"「🔓」で{ROLE_NAME}ロールを取得"))

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return

    # 「🔓」というメッセージに反応
    if message.content == '🔓':
        # ロールを取得（存在しなければ作成）
        role = get(message.guild.roles, name=ROLE_NAME)
        if not role:
            try:
                role = await message.guild.create_role(
                    name=ROLE_NAME,
                    mentionable=True,
                    reason='浮上用ロールの作成'
                )
                await message.channel.send(f"✅ ロール「{ROLE_NAME}」を作成しました。")
            except discord.Forbidden:
                await message.channel.send("❌ ロールを作成する権限がありません。")
                return

        # メンバーにロールを付与
        try:
            await message.author.add_roles(role)
            await message.channel.send(f"✅ {message.author.mention} に「{ROLE_NAME}」ロールを付与しました。")
        except discord.Forbidden:
            await message.channel.send("❌ ロールを付与する権限がありません。")
    
    # コマンドの処理を続行
    await bot.process_commands(message)

# ボットを実行
if __name__ == "__main__":
    if not TOKEN:
        print("エラー: .envファイルにDISCORD_TOKENを設定してください")
    else:
        bot.run(TOKEN)