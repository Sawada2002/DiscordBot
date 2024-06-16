import discord
from discord.ext import commands, tasks
import sqlite3
import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import atexit
import time

# 日本語フォントを設定
plt.rcParams['font.family'] = 'Noto Sans CJK JP'  # ここをシステムにインストールされた日本語フォント名に変更

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  # メッセージコンテンツへのアクセスを有効にする

bot = commands.Bot(command_prefix='!', intents=intents)

def adapt_datetime(ts):
    return ts.isoformat()

def convert_datetime(ts):
    return datetime.datetime.fromisoformat(ts.decode('utf-8'))

sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

def init_db():
    with sqlite3.connect('playtime.db', detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS playtime (
                user_id TEXT,
                game TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP
            )
        ''')
        conn.commit()

def close_active_sessions():
    with sqlite3.connect('playtime.db', detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        c = conn.cursor()
        end_time = datetime.datetime.now(datetime.timezone.utc)
        c.execute('''
            UPDATE playtime
            SET end_time = ?
            WHERE end_time IS NULL
        ''', (end_time,))
        conn.commit()

atexit.register(close_active_sessions)

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')
    update_playtime.start()

@bot.event
async def on_disconnect():
    close_active_sessions()

@tasks.loop(minutes=1)
async def update_playtime():
    retries = 5
    while retries > 0:
        try:
            with sqlite3.connect('playtime.db', detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                c = conn.cursor()
                end_time = datetime.datetime.now(datetime.timezone.utc)

                for guild in bot.guilds:
                    for member in guild.members:
                        if member.activity and isinstance(member.activity, discord.Game):
                            user_id = str(member.id)
                            game = member.activity.name
                            start_time = datetime.datetime.now(datetime.timezone.utc)

                            # このユーザーとゲームのアクティブなセッションがあるか確認する
                            c.execute('''
                                SELECT * FROM playtime
                                WHERE user_id = ? AND end_time IS NULL
                            ''', (user_id,))
                            active_session = c.fetchone()

                            if active_session:
                                if active_session[1] != game:
                                    # ゲームが変わった場合、前のゲームセッションを終了する
                                    c.execute('''
                                        UPDATE playtime
                                        SET end_time = ?
                                        WHERE user_id = ? AND end_time IS NULL
                                    ''', (end_time, user_id))
                                    # 新しいゲームのセッションを開始する
                                    c.execute('''
                                        INSERT INTO playtime (user_id, game, start_time, end_time)
                                        VALUES (?, ?, ?, ?)
                                    ''', (user_id, game, start_time, None))
                            else:
                                # アクティブなセッションがない場合、新しいセッションを開始する
                                c.execute('''
                                    INSERT INTO playtime (user_id, game, start_time, end_time)
                                    VALUES (?, ?, ?, ?)
                                ''', (user_id, game, start_time, None))
                        else:
                            # ユーザーがどのゲームもプレイしていない場合、アクティブセッションを終了する
                            c.execute('''
                                UPDATE playtime
                                SET end_time = ?
                                WHERE user_id = ? AND end_time IS NULL
                            ''', (end_time, str(member.id)))

                conn.commit()
            break  # 成功した場合、ループを抜ける
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                retries -= 1
                time.sleep(1)  # リトライの前に待機する
            else:
                raise

@bot.command()
async def myplaytime(ctx):
    user_id = str(ctx.author.id)
    with sqlite3.connect('playtime.db', detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT game, SUM((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24) as playtime
            FROM playtime
            WHERE user_id = ?
            GROUP BY game
            ORDER BY playtime DESC
        ''', (user_id,))
        
        rows = c.fetchall()

    if rows:
        games = [row[0] for row in rows]
        playtimes = [row[1] for row in rows]  # プレイ時間を時間単位で取得

        plt.figure(figsize=(10, 6))
        plt.barh(games, playtimes, color='skyblue')
        plt.xlabel('プレイ時間 (時間)')
        plt.title('あなたのプレイ時間')
        plt.gca().invert_yaxis()
        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, 'playtime.png'))
    else:
        await ctx.send('プレイ時間のデータが見つかりませんでした。')

@bot.command()
async def userplaytime(ctx):
    with sqlite3.connect('playtime.db', detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT user_id, game, SUM((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24) as playtime
            FROM playtime
            GROUP BY user_id, game
            ORDER BY playtime DESC
        ''')

        rows = c.fetchall()

    if rows:
        users_games = {}
        for row in rows:
            user_id = row[0]
            game = row[1]
            playtime = row[2]
            if user_id not in users_games:
                users_games[user_id] = {}
            users_games[user_id][game] = playtime

        for user_id, games in users_games.items():
            user = await bot.fetch_user(int(user_id))
            games_list = list(games.keys())
            playtimes_list = list(games.values())

            plt.figure(figsize=(10, 6))
            plt.barh(games_list, playtimes_list, color='skyblue')
            plt.xlabel('プレイ時間 (時間)')
            plt.title(f'{user.name}のプレイ時間')
            plt.gca().invert_yaxis()
            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            await ctx.send(file=discord.File(buffer, f'{user.name}_playtime.png'))
    else:
        await ctx.send('プレイ時間のデータが見つかりませんでした。')

init_db()

bot.run('token')
