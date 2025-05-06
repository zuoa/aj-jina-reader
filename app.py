import re
from urllib.parse import unquote

import requests
from fake_useragent import UserAgent
from flask import Flask
from openai import OpenAI

app = Flask(__name__)

# Patterns
SCRIPT_PATTERN = r"<[ ]*script.*?\/[ ]*script[ ]*>"
STYLE_PATTERN = r"<[ ]*style.*?\/[ ]*style[ ]*>"
META_PATTERN = r"<[ ]*meta.*?>"
COMMENT_PATTERN = r"<[ ]*!--.*?--[ ]*>"
LINK_PATTERN = r"<[ ]*link.*?>"
BASE64_IMG_PATTERN = r'<img[^>]+src="data:image/[^;]+;base64,[^"]+"[^>]*>'
SVG_PATTERN = r"(<svg[^>]*>)(.*?)(<\/svg>)"


def replace_svg(html: str, new_content: str = "this is a placeholder") -> str:
    return re.sub(
        SVG_PATTERN,
        lambda match: f"{match.group(1)}{new_content}{match.group(3)}",
        html,
        flags=re.DOTALL,
    )


def replace_base64_images(html: str, new_image_src: str = "#") -> str:
    return re.sub(BASE64_IMG_PATTERN, f'<img src="{new_image_src}"/>', html)


def clean_html(html: str, clean_svg: bool = False, clean_base64: bool = False):
    html = re.sub(
        SCRIPT_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        STYLE_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        META_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        COMMENT_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        LINK_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if clean_svg:
        html = replace_svg(html)
    if clean_base64:
        html = replace_base64_images(html)
    return html


def create_prompt(
    text: str, instruction: str = None, schema: str = None
) -> list:
    """
    Create a prompt for the model with optional instruction and JSON schema.
    """
    if not instruction:
        instruction = "Extract the main content from the given HTML and convert it to Markdown format."
    if schema:
        instruction = "Extract the specified information from a list of news threads and present it in a structured JSON format."
        prompt = f"{instruction}\n```html\n{text}\n```\nThe JSON schema is as follows:```json\n{schema}\n```"
    else:
        prompt = f"{instruction}\n```html\n{text}\n```"

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    return messages

@app.get('/<path:url>')
def reader(url):
    url = unquote(url)
    if not url.startswith('http'):
        return 'Invalid url', 400
    print(url)
    ua = UserAgent()
    headers = {
        'User-Agent': ua.random
    }
    html = requests.get(url, headers=headers).text

    if html:
        schema = """
        {
          "type": "object",
          "properties": {
            "title": {
              "type": "string"
            },
            "author": {
              "type": "string"
            },
            "date": {
              "type": "string"
            },
            "content": {
              "type": "string"
            }
          },
          "required": ["title", "author", "date", "content"]
        }
        """


        html = clean_html(html, clean_svg=True, clean_base64=True)

        messages = create_prompt(html)

        llm_model = "ReaderLM-v2"
        client = OpenAI(api_key="1", base_url="http://10.0.4.28:8081/v1/")
        try:
            response = client.chat.completions.create(
                model=llm_model,
                messages=messages,
                # temperature=0.1,
                stream=False,
                timeout=300
            )
            if response.choices:
                return response.choices[0].message.content
            else:
                return '', 500
        except Exception as e:
            return str(e), 500
        finally:
            client.close()
    else:
        return 'Fetch html error', 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6090, debug=True, use_reloader=False)
