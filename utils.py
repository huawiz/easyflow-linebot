import json

# 讀取 JSON 檔案
with open('story.json', 'r', encoding='utf-8') as file:
    scene_data = json.load(file)

def getSceneByKey(key):
    return next((scene['content'] for scene in scene_data['scenes'] if scene['key'] == key), None)

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

    

    def generate_buttons(self):
        return [
            {
                "type": "button",
                "action": {
                    "type": "message",
                    "label": option['text'],
                    "text": f"{'結局' if 'END' in option['next'] else '情節'}{option['next']}"
                },
                "style": "secondary",
                "height": "md",
                "adjustMode": "shrink-to-fit",
                "margin": "sm"
            }
            for opt, option in self.options.items()
            if option
        ]
    def end_buttons(self):
        return '''
        [
                {
                    "type": "button",
                    "action": {
                    "type": "message",
                    "label": "再產生一次結局",
                    "text": "結局{sceneID}"
                    },
                    "style": "secondary",
                    "adjustMode": "shrink-to-fit",
                    "margin": "5px"
                },
                {
                    "type": "button",
                    "action": {
                    "type": "message",
                    "label": "清除並重新開始",
                    "text": "情節A:清除並重新開始"
                    },
                    "style": "secondary",
                    "margin": "5px",
                    "adjustMode": "shrink-to-fit"
                }
          ]
        '''



