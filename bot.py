import os
import discord
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
import re

# .envファイルから環境変数を読み込む
load_dotenv()

# ボットの設定
TOKEN = os.getenv('DISCORD_TOKEN')

# インテントの設定
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.voice_states = True

# ボットを初期化
bot = commands.Bot(command_prefix=None, intents=intents)

# ボットユーザーを保持するグローバル変数
bot_user = None

@bot.event
async def on_ready():
    global bot_user
    bot_user = bot.user
    print(f'{bot_user.name} がDiscordに接続しました')

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author == bot_user:
        return
    
    # メッセージが空でないか確認
    if not message.content.strip():
        return
    
    # URLやメンションのみのメッセージは無視
    if message.content.startswith(('http://', 'https://', '<@', '#')):
        return
    
    try:
        # メッセージからカテゴリ名を取得（絵文字や記号を削除）
        clean_name = re.sub(r'[\W_]+', '', message.content.strip())
        if not clean_name:
            clean_name = 'new_channel'
        
        # ロール名（重複を避けるためユーザー名を含める）
        role_name = f'🔒 {clean_name[:20]} - {message.author.name}'
        
        # カテゴリ名
        category_name = f'📁 {message.content.strip()[:90]}'  # 長すぎる場合は切り詰め
        
        # カテゴリが既に存在するか確認
        category = get(message.guild.categories, name=category_name)
        
        # カテゴリが存在しない場合は作成
        if not category:
            # ロールを作成
            role = await message.guild.create_role(
                name=role_name,
                mentionable=True,
                reason=f'Created for {message.author}'
            )
            
            # 作成者にロールを付与
            await message.author.add_roles(role, reason='Channel creator role')
            
            # カテゴリの権限を設定
            overwrites = {
                message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                message.guild.me: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True,
                    stream=True
                )
            }
            
            # カテゴリを作成
            category = await message.guild.create_category(
                category_name,
                overwrites=overwrites
            )
            
            # テキストチャンネルを作成
            text_channel = await message.guild.create_text_channel(
                '💬-chat',
                category=category,
                reason=f'Created by {message.author}'
            )
            
            # ボイスチャンネルを作成
            voice_channel = await message.guild.create_voice_channel(
                '🔊-voice',
                category=category,
                reason=f'Created by {message.author}'
            )
            
            # 作成者にDMで通知
            try:
                embed = discord.Embed(
                    title='チャンネルを作成しました！',
                    description=(
                        f'カテゴリ: {category_name}\n'
                        f'テキストチャンネル: {text_channel.mention}\n'
                        f'ボイスチャンネル: {voice_channel.mention}\n\n'
                        f'**ロール**: {role.mention}\n'
                        'このロールを他のメンバーに付与すると、チャンネルにアクセスできるようになります。'
                    ),
                    color=discord.Color.green()
                )
                await message.author.send(embed=embed)
            except:
                pass  # DMがブロックされている場合は無視
            
            # 作成したチャンネルへのリンクを送信
            await message.channel.send(
                f'{message.author.mention} チャンネルを作成しました！\n'
                f'カテゴリ: {category.mention}\n'
                f'テキスト: {text_channel.mention}\n'
                f'ボイス: {voice_channel.mention}\n\n'
                f'**ロール**: {role.mention} を作成しました。\n'
                'このロールを他のメンバーに付与すると、チャンネルにアクセスできるようになります。'
            )
            
            # 元のメッセージを削除
            try:
                await message.delete()
            except:
                pass
        else:
            # 既存のカテゴリがある場合はその情報を表示
            text_channel = get(category.channels, name='💬-chat')
            voice_channel = get(category.channels, name='🔊-voice')
            
            # カテゴリに関連するロールを探す
            role = discord.utils.get(message.guild.roles, name=f'🔒 {clean_name[:20]} - {message.author.name}')
            
            if text_channel and voice_channel:
                message_text = (
                    f'{message.author.mention} このカテゴリは既に存在します！\n'
                    f'カテゴリ: {category.mention}\n'
                    f'テキスト: {text_channel.mention}\n'
                    f'ボイス: {voice_channel.mention}'
                )
                
                if role:
                    message_text += f'\n\n**ロール**: {role.mention}'
                
                await message.channel.send(message_text)
            
    except discord.Forbidden:
        await message.channel.send('❌ 権限が不足しています。管理者に連絡してください。')
    except Exception as e:
        await message.channel.send(f'❌ エラーが発生しました: {str(e)}')

# ボットを実行
if __name__ == "__main__":
    if not TOKEN:
        print("エラー: .envファイルにDISCORD_TOKENを設定してください")
    else:
        bot.run(TOKEN)
