from datetime import datetime
import re

async def read(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = text.content
    #会話保存
    with open('message_log.csv', 'a', encoding='utf-8') as file:
        file.write(f"{timestamp}, {text.author.display_name}, {content}\n")

    url_pattern = r'https?://x\.com[^\s]+'
    matches = re.findall(url_pattern, text.content)

    for match in matches:
        converted_message = text.content.replace(match, match.replace('x.com', 'vxtwitter.com'))
        await text.channel.send(f"{converted_message}")