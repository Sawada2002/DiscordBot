# main.py
import discord
from discord.ext import commands
import pandas as pd
from datetime import datetime
import readMessage
import sleep
import discord
from discord.ext import commands, tasks
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import re

opa = []
wake_up_times = [] # 起床時間を記録するためのリスト
target_channel_id = 11111 #チャンネルID

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await readMessage.read(message)

    if message.content.startswith('おぱ'):
        await sleep.opa(message.author.name)
    await bot.process_commands(message)

@bot.command(name='グラフ')
async def show_graph(ctx):
    df = pd.read_csv('sleepTime.csv', names=['datetime', 'user']) #sleepTime.csvの読み込み

    # 日付と時間を分割，新しい列に追加する
    df['datetime'] = pd.to_datetime(df['datetime'])  # 文字列->日時
    df['date'] = df['datetime'].dt.date
    df['time'] = df['datetime'].dt.time

    # 時間を数値に変換する関数
    def time_to_numeric(time):
        return time.hour * 3600 + time.minute * 60 + time.second + time.microsecond / 1e6

    df['time_numeric'] = df['time'].apply(time_to_numeric)
    plt.figure(figsize=(10,6))
    for user, group in df.groupby('user'):
        plt.plot(group['date'], group['time_numeric'] / 3600, label=user)

    plt.title('Opa-Time')
    plt.legend()
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))

    filename = 'opa.png'
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(filename)  
    plt.close()  

    # グラフをDiscordに送信
    target_channel = bot.get_channel(target_channel_id)
    if target_channel:
        with open(filename, 'rb') as file:
            await target_channel.send('起床時間の推移です', file=discord.File(file))
    else:
        print(f'無効なチャンネルID: {target_channel_id}')





# 以下の部分に Discord ボットのトークンを入力してください。
token = 'token'

if __name__ == "__main__":
    bot.run(token)
