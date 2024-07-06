import logging
import os
import re
import sys

if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv

    load_dotenv()

import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,FlexMessage,FlexContainer
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import uvicorn
import requests

logging.basicConfig(level=os.getenv('LOG', 'WARNING'))
logger = logging.getLogger(__file__)

app = FastAPI()

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

configuration = Configuration(
    access_token=channel_access_token
)

async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
parser = WebhookParser(channel_secret)

from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.generativeai as genai
from firebase import firebase
from utils import Scene,json_str,scene_data,End,end_json,end_data
from fastapi.staticfiles import StaticFiles
# Mount the static files
app.mount("/static", StaticFiles(directory="static"), name="static")

firebase_url = os.getenv('FIREBASE_URL')
gemini_key = os.getenv('GEMINI_API_KEY')


# Initialize the Gemini Pro API
genai.configure(api_key=gemini_key)


@app.get("/health")
async def health():
    return 'ok'


@app.post("/webhooks/line")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        logging.info(event)
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessageContent):
            continue
        text = event.message.text
        user_id = event.source.user_id

        msg_type = event.message.type
        fdb = firebase.FirebaseApplication(firebase_url, None)
        if event.source.type == 'group':
            user_chat_path = f'chat/{event.source.group_id}'
        else:
            user_chat_path = f'chat/{user_id}'
            chat_state_path = f'state/{user_id}'
        chatgpt = fdb.get(user_chat_path, None)
        

        if text.find('情節') != -1 and msg_type == 'text':
            
            if chatgpt is None:
                messages = []
            else:
                messages = chatgpt

            sceneID_match = re.search(r'情節\s*([A-Za-z0-9]+)', text.split(':')[0])
            if sceneID_match:
                sceneID = sceneID_match.group(1)
            else:
                sceneID = 'A'
            scene = Scene(sceneID)
            
            bubble_string = '''
            {
                "type": "carousel",
                "contents": [
                {
                    "type": "bubble",
                    "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "image",
                        "url": "[picURL]",
                        "size": "full",
                        "aspectMode": "cover",
                        "aspectRatio": "2:3",
                        "gravity": "top"
                        }
                    ],
                    "paddingAll": "0px"
                    }
                },
                {
                    "type": "bubble",
                    "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "劇情",
                        "wrap": true,
                        "color": "#000000",
                        "size": "xxl",
                        "flex": 5,
                        "weight": "bold"
                        }
                    ]
                    },
                    "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "[scene_text]",
                        "maxLines": 10,
                        "wrap": true
                        }
                    ]
                    },
                    "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [button]
                        }
                    ]
                    }
                }
                ]
            }
            '''
            
            # 圖片
            bubble_string = bubble_string.replace('[picURL]',request.url_for('static', path=f"{sceneID}.png"))

            # 劇情
            bubble_string = bubble_string.replace('[scene_text]',scene.text)
            logging.info(scene.text)
            
            # 產生選項按鈕
            bubble_string = bubble_string.replace('[button]',json.dumps(scene.generate_buttons(), ensure_ascii=False, indent=2))
            #logging.info(bubble_string)

            # 產生FlexMessage
            msg = FlexMessage(alt_text=text, contents=FlexContainer.from_json(bubble_string))    
            


            messages.append({'role': 'user', 'scene': scene.text+'\n','action':text.split(':')[1]})
            # 更新firebase中的對話紀錄
            fdb.put_async(user_chat_path, None, messages)
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[msg]
                ))
        elif text.find('結局') != -1 and msg_type == 'text':
            END_match = re.search(r'結局\s*([A-Za-z0-9]+)', text)

            # 讀Firebase資料
            if chatgpt is None:
                messages = []
            else:
                messages = chatgpt

            if END_match:
                endID = END_match.group(1)
            
            model = genai.GenerativeModel('gemini-pro')
            
            try:
                response = model.generate_content(
                    f'現在我們有一段感情故事，故事內容如下，請幫我產生結局文字，文字最多100字:\n\n\n{messages}',
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )

                # 檢查是否有內容被阻止
                if response.prompt_feedback.block_reason:
                    print(f"Content was blocked. Reason: {response.prompt_feedback.block_reason}")
                    generated_text = "抱歉，無法生成適當的結局。"
                else:
                    # 使用 parts 來獲取生成的文本
                    generated_text = response.text
                    if not generated_text:
                        generated_text = "抱歉，生成的結局為空。"
                
                print(f"Generated text: {generated_text}")

            except ValueError as ve:
                print(f"ValueError occurred: {ve}")
                generated_text = "抱歉，我無法生成適當的結局。"
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                generated_text = "發生了意外錯誤，請稍後再試。"

            #end_scene = End(endID)
            bubble_string = '''
            {
            "type": "bubble",
            "size": "giga",
            "hero": {
                "type": "image",
                "size": "full",
                "aspectRatio": "13:20",
                "aspectMode": "cover",
                "url": "[picURL]"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "text",
                    "text": "[end_text]",
                    "wrap": true
                }
                ]
            }
            }
            '''
            bubble_string = bubble_string.replace('[picURL]',request.url_for('static', path=f"{endID}.png"))
            print(generated_text)
            bubble_string = bubble_string.replace('[end_text]', generated_text)  # 使用生成的文本
            msg = FlexMessage(alt_text=text, contents=FlexContainer.from_json(bubble_string)) 
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[msg]
                ))
        elif text == '清空' and msg_type == 'text':
            fdb.delete(user_chat_path, None)

        else:
            if chatgpt is None:
                messages = []
            else:
                messages = chatgpt
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                    f'{text}',
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
            reply_msg = response.text
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_msg)]
                ))
            
        
            
            
        
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', default=8080))
    debug = True if os.environ.get(
        'API_ENV', default='develop') == 'develop' else False
    logging.info('Application will start...')
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=debug)
