import logging
import os
import re
import sys
import json
from fastapi import FastAPI, HTTPException, Request
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,FlexMessage,FlexContainer,ShowLoadingAnimationRequest
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import uvicorn

from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.generativeai as genai
from firebase import firebase
from utils import Scene,scene_data
from fastapi.staticfiles import StaticFiles

if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv

    load_dotenv()



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

        user_chat_path = f'chat/{user_id}'
        chatgpt = fdb.get(user_chat_path, None)
       


        if ('情節' in text[:5] or '結局' in text[:5]) and msg_type == 'text':
            messages = chatgpt if chatgpt is not None else []
            if '情節' in text[:5]:
                match = re.search(r'情節\s*([A-Za-z0-9]+)', text.split(':')[0])
                sceneID = match.group(1) if match else None
                scene = Scene(sceneID) if match else None
                if text.split(':')[1] == "清除並重新開始":
                    fdb.delete_async(user_chat_path, None)
                    
            else:
                match = re.search(r'結局\s*([A-Za-z0-9]+)', text.split(':')[0])
                sceneID = match.group(1) if match else None
                scene = Scene(sceneID) 
            


            bubble_string = '''
           {
            "type": "bubble",
            "size": "giga",
            "hero": {
                "type": "image",
                "size": "full",
                "aspectRatio": "21:13",
                "aspectMode": "cover",
                "url": "{picURL}"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "text",
                    "text": "{scene_text}",
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
                        "contents": {button}
                        }
                    ]
                    }
            }
            '''
            
            # 圖片
            
 
            # 產生選項按鈕
            if '情節' in text[:5]:
                bubble_string = bubble_string.replace('{picURL}',os.getenv('url') + f"static/{sceneID}.png")
                logging.info(os.getenv('url') + f"static/{sceneID}.png")
                bubble_string = bubble_string.replace('{scene_text}',scene.text)
                bubble_string = bubble_string.replace('{button}',json.dumps(scene.generate_buttons(), ensure_ascii=False, indent=2))
                # 更新firebase中的對話紀錄
                messages.append({'userid':event.source.user_id,'type':'plot','role': 'user', 'scene': scene.text+'\n','action':text.split(':')[1]})
                fdb.put_async(user_chat_path, None, messages)
            else:
                # 產生loading animation
                bubble_string = bubble_string.replace('{picURL}',os.getenv('url') + f"static/{sceneID}.png")
                logging.info(os.getenv('url') + f"static/{sceneID}.png")
                await line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chatId=event.source.user_id, loadingSeconds=5))
                # 產生結局文字
                model = genai.GenerativeModel('gemini-pro')
                
                response = model.generate_content(
                    f'現在我們有一段感情故事，故事內容如下，請幫我產生結局文字，文字最多100字:\n\n\n{messages}',
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                bubble_string = bubble_string.replace('{scene_text}', response.text)
                bubble_string = bubble_string.replace('{button}',scene.end_buttons())
                bubble_string = bubble_string.replace('{sceneID}',sceneID)
                messages.append({'userid':event.source.user_id,'type':'end','role': 'user', 'scene': response.text+'\n','action':text})
                fdb.put_async(user_chat_path, None, messages)

            # 產生FlexMessage
            msg = FlexMessage(alt_text=text, contents=FlexContainer.from_json(bubble_string))    
            
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[msg]
                ))
        elif text == '清除紀錄' and msg_type == 'text':
            await line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chatId=event.source.user_id, loadingSeconds=5))
            fdb.delete(user_chat_path, None)
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text='紀錄已清除')]
                ))

        elif text == '獲取目前摘要' and msg_type == 'text':
            messages = chatgpt if chatgpt is not None else []
            await line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chatId=event.source.user_id, loadingSeconds=5))
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                    f'Summary the following message which userid is {event.source.user_id} in 繁體中文 by less 5 list points. 如果無對應userid的訊息，請回答"無"。  \n{messages}',
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
        """
        else:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                    f'{text}(請使用繁體中文回答)',
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
        """
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
