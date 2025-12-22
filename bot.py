import discord
import os
import re
import json
import logging
from typing import Dict, List, Set, Optional, Union
from collections import defaultdict, deque
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# 設定ファイルのパス
CONFIG_FILE = 'bot_config.json'

# 環境変数の読み込み
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class AntiSpamBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        
        # 設定の読み込み
        self.config = self.load_config()
        
        # スパム検出の設定
        self.user_message_history = defaultdict(list)
        self.user_message_content = defaultdict(deque)
        self.user_mentions = defaultdict(list)
        
        # 設定可能なパラメータ
        self.spam_threshold = self.config.get('spam_threshold', 5)
        self.spam_time_window = self.config.get('spam_time_window', 10)
        self.dupe_threshold = self.config.get('dupe_threshold', 3)
        self.mention_limit = self.config.get('mention_limit', 5)
        self.caps_ratio = self.config.get('caps_ratio', 0.7)
        self.max_duplicate_chars = self.config.get('max_duplicate_chars', 5)
        
        # ブロックするURLパターン
        self.blocked_domains = set(self.config.get('blocked_domains', [
            'discord.gg/',
            'discord.com/invite/',
            'example.com',
        ]))
        
        # ホワイトリスト
        self.whitelist_roles = set(self.config.get('whitelist_roles', ['Admin', 'Moderator']))
        self.whitelist_users = set(self.config.get('whitelist_users', []))
        
        # コマンドを登録
        self.tree.command(
            name="whitelist",
            description="ホワイトリストを管理します",
            guild=None  # グローバルコマンドとして登録
        )(
            app_commands.describe(
                action="実行するアクション (add/remove/list)",
                user="追加・削除するユーザー (listの場合は不要)"
            )(
                app_commands.checks.has_permissions(administrator=True)(
                    self._whitelist_command
                )
            )
        )
        
    async def setup_hook(self):
        # スラッシュコマンドを登録
        try:
            # コマンドを追加
            self.tree.add_command(self.whitelist_command)
            
            # コマンドを同期（グローバルコマンドとして登録）
            logger.info('スラッシュコマンドを同期中...')
            
            # 既存のコマンドをクリア（必要に応じて）
            # self.tree.clear_commands(guild=None)
            
            # コマンドを同期
            synced = await self.tree.sync()
            
            # 同期されたコマンドをログに出力
            logger.info(f'同期したスラッシュコマンド ({len(synced)}個):')
            for cmd in synced:
                logger.info(f'- /{cmd.name}: {cmd.description}')
                
            # サーバーごとのコマンドも確認
            for guild in self.guilds:
                guild_synced = await self.tree.sync(guild=guild)
                if guild_synced:
                    logger.info(f'サーバー "{guild.name}" で同期したコマンド ({len(guild_synced)}個)')
                    
        except Exception as e:
            logger.error(f'スラッシュコマンドの同期に失敗: {type(e).__name__}: {e}', exc_info=True)
            raise

    async def _whitelist_command(self, interaction: discord.Interaction, action: str, user: Optional[discord.Member] = None) -> None:
        """
        ホワイトリストを管理するコマンド
        
        Parameters
        ----------
        interaction : discord.Interaction
            インタラクションオブジェクト
        action : str
            実行するアクション (add/remove/list)
        user : Optional[discord.Member], optional
            追加・削除するユーザー (listの場合は不要), by default None
        """
        try:
            action = action.lower()
            
            if action == 'add' and user:
                self.whitelist_users.add(str(user.id))
                self.save_config()
                await interaction.response.send_message(
                    f'✅ {user.mention} をホワイトリストに追加しました',
                    ephemeral=True
                )
                
            elif action == 'remove' and user:
                user_id = str(user.id)
                if user_id in self.whitelist_users:
                    self.whitelist_users.remove(user_id)
                    self.save_config()
                    await interaction.response.send_message(
                        f'✅ {user.mention} をホワイトリストから削除しました',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'❌ {user.mention} はホワイトリストに登録されていません',
                        ephemeral=True
                    )
                    
            elif action == 'list':
                if not self.whitelist_users:
                    await interaction.response.send_message('ホワイトリストは空です', ephemeral=True)
                    return
                    
                user_list = []
                for uid in self.whitelist_users:
                    member = interaction.guild.get_member(int(uid))
                    user_list.append(f'- {member.mention if member else f"Unknown User ({uid})"}')
                
                embed = discord.Embed(
                    title='ホワイトリスト登録ユーザー',
                    description='\n'.join(user_list) or 'なし',
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            else:
                await interaction.response.send_message(
                    '使い方:\n'
                    '`/whitelist add @ユーザー` - ユーザーをホワイトリストに追加\n'
                    '`/whitelist remove @ユーザー` - ユーザーをホワイトリストから削除\n'
                    '`/whitelist list` - ホワイトリストのユーザーを表示',
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f'ホワイトリストコマンドでエラー: {e}', exc_info=True)
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        '❌ コマンドの実行中にエラーが発生しました',
                        ephemeral=True
                    )
                except Exception as send_error:
                    logger.error(f'エラーメッセージの送信に失敗: {send_error}')

    async def on_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """スラッシュコマンドのエラーハンドラー"""
        if isinstance(error, app_commands.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    '❌ このコマンドを実行する権限がありません',
                    ephemeral=True
                )
        else:
            logger.error(f'コマンドエラー: {error}', exc_info=True)
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        '❌ コマンドの実行中にエラーが発生しました',
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f'エラーメッセージの送信に失敗: {e}')
        
        # コマンドの追加
        self.setup_commands()

    def load_config(self) -> dict:
        """設定をファイルから読み込む"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def save_config(self):
        """設定をファイルに保存"""
        config = {
            'spam_threshold': self.spam_threshold,
            'spam_time_window': self.spam_time_window,
            'dupe_threshold': self.dupe_threshold,
            'mention_limit': self.mention_limit,
            'caps_ratio': self.caps_ratio,
            'max_duplicate_chars': self.max_duplicate_chars,
            'blocked_domains': list(self.blocked_domains),
            'whitelist_roles': list(self.whitelist_roles),
            'whitelist_users': list(self.whitelist_users),
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    async def setup_hook(self):
        """ボット起動時にスラッシュコマンドを同期"""
        await self.tree.sync()
        print(f'スラッシュコマンドを同期しました')
    
    def is_whitelisted(self, member: discord.Member) -> bool:
        """ユーザーがホワイトリストに含まれているか確認"""
        # サーバーオーナーは常に許可
        if member.guild.owner_id == member.id:
            return True
            
        # ホワイトリストのロールを持っているか確認
        if any(role.name in self.whitelist_roles for role in member.roles):
            return True
            
        # ユーザーIDがホワイトリストに含まれているか確認
        if str(member.id) in self.whitelist_users:
            return True
            
        return False

    async def on_ready(self):
        logger.info(f'{self.user} がログインしました。')
        logger.info(f'Bot ID: {self.user.id}')
        logger.info(f'サーバー数: {len(self.guilds)}')
        
        try:
            # コマンドを同期
            await self.setup_hook()
            logger.info('起動が完了しました。スラッシュコマンドが利用可能です。')
        except Exception as e:
            logger.error(f'起動中にエラーが発生しました: {e}', exc_info=True)
            await self.close()

    def check_message_content(self, message: discord.Message) -> List[str]:
        """メッセージの内容をチェックして、問題があれば理由を返す"""
        content = message.content
        author = message.author
        issues = []
        
        # 大文字の乱用チェック
        if len(content) > 10:  # 短いメッセージは無視
            upper_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if upper_ratio > self.caps_ratio:
                issues.append(f'大文字の乱用 (大文字率: {upper_ratio*100:.1f}%)')
        
        # 連続する同じ文字のチェック
        if re.search(r'(.)\1{' + str(self.max_duplicate_chars) + ',}', content):
            issues.append('連続する同じ文字の乱用')
        
        # ブロックされたURLのチェック
        for domain in self.blocked_domains:
            if domain.lower() in content.lower():
                issues.append(f'ブロックされたドメイン: {domain}')
                break
        
        # 招待リンクのチェック
        if 'discord.gg/' in content.lower() or 'discord.com/invite/' in content.lower():
            if not self.is_whitelisted(author):
                issues.append('許可されていない招待リンク')
        
        # メンションのチェック
        if len(message.mentions) > self.mention_limit:
            issues.append(f'メンションの乱用 ({len(message.mentions)}回)')
        
        return issues
    
    async def check_duplicate_messages(self, message: discord.Message) -> bool:
        """同じメッセージの繰り返しをチェック"""
        user_id = message.author.id
        content = message.content.strip()
        
        # メッセージが空や短すぎる場合は無視
        if len(content) < 5:
            return False
            
        # ユーザーの直近のメッセージを取得
        recent_messages = self.user_message_content[user_id]
        
        # 同じ内容のメッセージが連続して送信されていないか確認
        duplicate_count = 0
        for msg, timestamp in recent_messages:
            if msg == content:
                duplicate_count += 1
                if duplicate_count >= self.dupe_threshold - 1:  # 現在のメッセージを含めて閾値を超えるか
                    return True
            else:
                # 異なるメッセージが来たらカウントをリセット
                duplicate_count = 0
                
        return False
    
    async def punish_user(self, message: discord.Message, reason: str):
        """スパマーを処罰"""
        try:
            # ユーザーをBAN
            await message.author.ban(
                reason=f'スパム行為のためBAN: {reason}',
                delete_message_days=1
            )
            
            # ログを送信
            log_msg = (
                f'🚨 **ユーザーがBANされました**\n'
                f'**ユーザー**: {message.author.mention} (`{message.author.id}`)\n'
                f'**理由**: {reason}\n'
                f'**チャンネル**: {message.channel.mention}'
            )
            
            # ログチャンネルを探す
            log_channel = discord.utils.get(message.guild.text_channels, name='mod-log')
            if not log_channel:
                log_channel = message.channel
                
            await log_channel.send(log_msg)
            
            # スパムメッセージを削除
            try:
                await message.delete()
            except:
                pass
                
        except discord.Forbidden:
            print(f'権限エラー: {message.author} をBANできませんでした')
        except Exception as e:
            print(f'エラーが発生しました: {e}')
    
    async def on_message(self, message):
        # DMは無視
        if not message.guild:
            return
            
        # ボット自身のメッセージは無視
        if message.author.bot:
            return
            
        # ホワイトリストユーザーはスキップ
        if self.is_whitelisted(message.author):
            return

        current_time = datetime.utcnow()
        user_id = message.author.id
        
        # メッセージ履歴を更新
        self.user_message_history[user_id].append(current_time)
        
        # メッセージ内容を記録（重複チェック用）
        self.user_message_content[user_id].append((message.content.strip(), current_time))
        
        # 古いデータを削除
        self.user_message_history[user_id] = [
            t for t in self.user_message_history[user_id] 
            if current_time - t < timedelta(seconds=self.spam_time_window)
        ]
        
        # メッセージ履歴もクリーンアップ
        self.user_message_content[user_id] = [
            (msg, t) for msg, t in self.user_message_content[user_id]
            if current_time - t < timedelta(seconds=self.spam_time_window * 2)
        ]
        
        # 各種チェックを実行
        issues = []
        
        # 1. メッセージフラッドチェック
        if len(self.user_message_history[user_id]) > self.spam_threshold:
            issues.append(f'メッセージフラッド ({len(self.user_message_history[user_id])}回/10秒)')
        
        # 2. メッセージ内容のチェック
        content_issues = await self.check_message_content(message)
        issues.extend(content_issues)
        
        # 3. 重複メッセージのチェック
        if await self.check_duplicate_messages(message):
            issues.append(f'同じメッセージの繰り返し (連続{self.dupe_threshold}回以上)')
        
        # 問題があれば処罰
        if issues:
            reason = ', '.join(issues)
            await self.punish_user(message, reason)

# ボットを起動
if __name__ == "__main__":
    if TOKEN:
        bot = AntiSpamBot()
        bot.run(TOKEN)
    else:
        print("エラー: DISCORD_TOKENが設定されていません。")
