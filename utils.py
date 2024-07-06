import os
import json


# JSON 字符串
json_str = '''
{
  "scenes": [
    {
      "key": "A",
      "content": [{
        "text": "當你們吃完浪漫的燭光晚餐，回到旅館房間，現在你要...?",
        "pic": "",
        "opt_a": [{
          "text": "不管怎樣先搶浴室",
          "next": "B2"
        }],
        "opt_b": [{
          "text": "有點尷尬那我來放音樂",
          "next": "B1"
        }],
        "opt_c": [{
          "text": "坐在床邊看他要幹嘛我再來決定我要幹嘛",
          "next": "B1"
        }]
      }]
    },
    {
      "key": "B1",
      "content": [{
        "text": "你們輪流洗澡後，坐在床上聊天分享今天出遊的心情，很溫馨又愉快，這時，對方慢慢靠近你，你也很喜歡他的靠近，這時你會...?",
        "pic": "",
        "opt_a": [{
          "text": "先發制人吻上去",
          "next": "C1"
        }],
        "opt_b": [{
          "text": "假裝鎮定等他先動作",
          "next": "C1"
        }],
        "opt_c": [{
          "text": "覺得發展太快把頭撇開",
          "next": "C2"
        }]
      }]
    },
    {
      "key": "B2",
      "content": [{
        "text": "正在淋浴邊想著今天美好的回憶時，浴室門傳出敲門聲，示意想要一起洗，這時你會？",
        "pic": "",
        "opt_a": [{
          "text": "假裝沒人在裡面，默默把水關掉",
          "next": "C2"
        }],
        "opt_b": [{
          "text": "門開了一個小縫，暗示他進來",
          "next": "C1"
        }]
      }]
    },
    {
      "key": "C1",
      "content": [{
        "text": "燈光美氣氛佳，你們發生性行為，當下你也很開心，他突然說：親愛的你好帥/你好美，可不可以讓我拍幾張照片，保證只是留念而已...",
        "pic": "",
        "opt_a": [{
          "text": "好啊我們互拍，當做情侶間的情趣",
          "next": "D1"
        }],
        "opt_b": [{
          "text": "內心覺得不妥，但當下沒有拒絕",
          "next": "D1"
        }],
        "opt_c": [{
          "text": "搖頭說不太好，你想暫停冷靜一下",
          "next": "D2"
        }]
      }]
    },
    {
      "key": "C2",
      "content": [{
        "text": "這時你們有點尷尬，對方說：親愛的你是不是不愛我...",
        "pic": "",
        "opt_a": [{
          "text": "誠實說我覺得發展太快了，還沒準備好",
          "next": "D3"
        }],
        "opt_b": [{
          "text": "急忙說我愛你，接著吻上去",
          "next": "D4"
        }],
        "opt_c": [{
          "text": "不講話",
          "next": "D2"
        }]
      }]
    },
    {
      "key": "D1",
      "content": [{
        "text": "你們結束兩天一夜小旅行，感情急速升溫，你非常開心。某天IG突然收到陌生訊息：你身材很好耶，有在約嗎～！",
        "pic": "",
        "opt_a": [{
          "text": "戀愛的甜蜜背後隱藏許多風險，如果發現自己私密照外流，你可以...（chatbot提供報警方式＆心輔資源）",
          "next": "END1"
        }]
      }]
    },
    {
      "key": "D2",
      "content": [{
        "text": "對方露出哀求的表情：我愛你才想這麼做、我保證我會更愛你！你的內心開始有點動搖...",
        "pic": "",
        "opt_a": [{
          "text": "戀愛的甜蜜背後隱藏許多風險，愛他不等於要答應他...（chatbot解釋什麼是情侶間的PUA）",
          "next": "END3"
        }]
      }]
    },
    {
      "key": "D3",
      "content": [{
        "text": "你們結束兩天一夜小旅行，接下來逐漸發現兩人價值觀的差異，最後和平分手...",
        "pic": "",
        "opt_a": [{
          "text": "戀愛的甜蜜背後隱藏許多風險，未來你遇到不知道該怎麼辦的狀況，可以先找簡單愛。事務所詢問歐！",
          "next": "END2"
        }]
      }]
    },
    {
      "key": "D4",
      "content": [{
        "text": "你們發生性行為，他突然說：親愛的你好帥/你好美，可不可以讓我拍幾張照片，保證只是留念而已...",
        "pic": "",
        "opt_a": [{
          "text": "好啊我們互拍，當做情侶間的情趣",
          "next": "E1"
        }],
        "opt_b": [{
          "text": "內心覺得不妥，但當下沒有拒絕",
          "next": "E1"
        }],
        "opt_c": [{
          "text": "搖頭說不太好，你想暫停冷靜一下",
          "next": "E2"
        }]
      }]
    },
    {
      "key": "E1",
      "content": [{
        "text": "你們結束兩天一夜小旅行，感情急速升溫，你非常開心。某天IG突然收到陌生訊息：你身材很好耶，有在約嗎～！",
        "pic": "",
        "opt_a": [{
          "text": "123",
          "next": "END2"
        }]
      }]
    },
    {
      "key": "E2",
      "content": [{
        "text": "對方露出哀求的表情：我愛你才想這麼做、我保證我會更愛你！你的內心開始有點動搖...",
        "pic": "",
        "opt_a": [{
          "text": "123",
          "next": "END3"
        }]
      }]
    }
  ]
}
'''

data = json.loads(json_str)
def getSceneByKey(key):
    return next((scene['content'] for scene in data['scenes'] if scene['key'] == key), None)

class Scene:
    def __init__(self, key):
        self.key = key
        self.content = getSceneByKey(self.key)
        if self.content:
            self.text = self.content[0].get('text', '')
            self.pic = self.content[0].get('pic', '')
            self.options = {
                opt: self._get_option(f'opt_{opt}') for opt in 'abc'
            }

    def _get_option(self, opt_key):
        if self.content and opt_key in self.content[0]:
            option = self.content[0][opt_key][0]
            return {
                'text': option.get('text', ''),
                'next': option.get('next', '')
            }
        return None

    def get_option_text(self, option):
        return self.options.get(option, {}).get('text', '')

    def get_next_scene_key(self, option):
        return self.options.get(option, {}).get('next', '')

    def generate_buttons(self):
        return [
            {
                "type": "button",
                "action": {
                    "type": "message",
                    "label": option['text'],
                    "text": "情節 "+option['next']
                },
                "style": "secondary",
                "height": "md",
                "adjustMode": "shrink-to-fit",
                "margin": "sm"
            }
            for opt, option in self.options.items()
            if option
        ]

    def __str__(self):
        return f"Scene(key={self.key}, text={self.text}, options={self.options})"

def main():
    try:
        scene = Scene("D3")
        buttons = scene.generate_buttons()
        if buttons:
            print(json.dumps(scene.generate_buttons(), ensure_ascii=False, indent=2))
        else:
            print("沒有可用的按鈕選項。")
    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()