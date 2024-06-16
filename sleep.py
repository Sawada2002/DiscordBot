import pandas as pd
from datetime import datetime
import main

async def opa(username):
    current_time = datetime.now()
    main.opa.append((current_time, username))
    #print(f'{username} 起きました {current_time}') #log確認用
    await save_to_csv(current_time, username) #csvに保存する関数

#起きた時間とユーザ名をcsvに保存する
async def save_to_csv(time, name): 
    df = pd.DataFrame([(time, name)]) #時間，名前で保存
    df.to_csv('sleepTime.csv', mode='a', header=False, index=False) #mode=aは上書きではなく，どんどん付け足していくモード
