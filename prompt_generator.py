import json
import os
import random
import urllib.error
import urllib.request

from .nodes import StringExtractPrompt

def _config():
    """接続設定を返す。OSの環境変数 > 同階層の .env の順で優先（.env は毎回読むので再起動不要）"""
    values = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    get = lambda k, d: os.environ.get(k) or values.get(k) or d
    base = get("LMSTUDIO_BASE_URL", "http://localhost:1234").strip().rstrip("/")
    if "://" not in base:  # "192.168.1.10:1234" のようにスキームなしでも可
        base = "http://" + base
    if base.endswith("/v1"):
        base = base[:-3]
    return base, get("LMSTUDIO_API_KEY", "lm-studio")


def _request(method, url, key, payload=None, timeout=10):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def _find_loaded_model(base, key):
    """ロード済みLLMのモデルキーを返す。取得できなければ None"""
    try:
        data = _request("GET", base + "/api/v0/models", key)
        for m in data.get("data", []):
            if m.get("state") == "loaded" and m.get("type") in ("llm", "vlm"):
                return m.get("id")
    except Exception:
        pass
    return None


DEFAULT_SYSTEM_PROMPT = (
    "あなたは画像生成AI用のプロンプトを作るアシスタントです。\n"
    "- 与えられたテーマから、画像生成プロンプトを英語で1つ作成してください。\n"
    "- 毎回異なるプロンプトを生成してください。\n"
    "- 再現性を高めるため、被写体・構図・照明・色彩・質感・画風・カメラ/レンズなど、"
    "細部に至るまで可能な限り詳細に記述してください。\n"
    "- 思考過程・説明・前置きは絶対に出力しないでください。"
)

_TEXT_FORMAT_HINT = (
    "\n\n出力形式（この形式のみを出力すること）:\n"
    "PROMPT: <画像生成プロンプト>"
)
_TEXT_FORMAT_HINT_NEG = _TEXT_FORMAT_HINT + "\nNEGATIVE: <ネガティブプロンプト>"


class LMStudioPromptGenerator:
    """テーマ → LM Studio で生成 → prompt / negative_prompt を抽出、までを1ノードで行う"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "theme": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": "ユーザーメッセージ。生成したい画像のテーマ",
                }),
                "system_prompt": ("STRING", {
                    "multiline": True, "default": DEFAULT_SYSTEM_PROMPT,
                    "tooltip": "LLMへの指示。出力形式の指定は不要（ノードが自動で付与する）",
                }),
                "model_key": ("STRING", {
                    "multiline": False, "default": "",
                    "tooltip": "LM Studio のモデルキー。空欄ならロード済みモデルを使用",
                }),
                "structured_output": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "True=JSON Schema で出力形式を強制（推奨）/ False=テキスト出力から抽出",
                }),
                "generate_negative": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "True=negative_prompt も生成させる",
                }),
                "seed": ("INT", {
                    "default": -1, "min": -1, "max": 0xffffffffffffffff,
                    "tooltip": "-1 = 実行のたびにランダム",
                }),
            },
            "optional": {
                "max_tokens": ("INT", {"default": 4096, "min": 1, "max": 131072}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "auto_unload": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "生成後にモデルをアンロードする（unload_delay=0 のとき即時）",
                }),
                "unload_delay": ("INT", {
                    "default": 0, "min": 0, "max": 3600,
                    "tooltip": "auto_unload 有効時、最後の利用からこの秒数後にアンロード（TTL）。0=即時",
                }),
                "timeout_seconds": ("INT", {"default": 300, "min": 10, "max": 3600}),
                "strip_thinking": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "raw_text から思考ブロックを除去する",
                }),
                "debug": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("prompt", "negative_prompt", "raw_text", "method_used", "success")
    FUNCTION = "generate"
    CATEGORY = "String Function"
    DESCRIPTION = (
        "LM Studio でプロンプトを生成し、prompt / negative_prompt を抽出します。"
        "接続先（リモート可）は .env の LMSTUDIO_BASE_URL で指定します"
    )

    @classmethod
    def IS_CHANGED(cls, seed=-1, **kwargs):
        return float("nan") if seed == -1 else seed

    # ------------------------------------------------------------------ #
    @staticmethod
    def _schema(generate_negative):
        props = {
            "prompt": {
                "type": "string",
                "description": "Image generation prompt in English. No explanations.",
            },
        }
        if generate_negative:
            props["negative_prompt"] = {
                "type": "string",
                "description": "Negative prompt. Comma-separated elements to avoid.",
            }
        return {
            "type": "object",
            "properties": props,
            "required": list(props),
            "additionalProperties": False,
        }

    def _chat(self, base, key, payload, timeout, debug):
        if debug:
            print(f"[SFn LMStudio] POST {base}/v1/chat/completions\n{json.dumps(payload, ensure_ascii=False)[:1500]}")
        try:
            body = _request("POST", base + "/v1/chat/completions", key, payload, timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"LM Studio がエラーを返しました (HTTP {e.code}): {detail}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RuntimeError(
                f"LM Studio に接続できません ({base}): {e}。"
                "サーバーの起動、リモートの場合は LM Studio の「ローカルネットワークで提供」設定、"
                "ファイアウォール、.env の LMSTUDIO_BASE_URL を確認してください"
            ) from e
        try:
            return body["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise RuntimeError(f"LM Studio の応答形式が不正です: {str(body)[:300]}") from e

    @staticmethod
    def _unload(base, key, model_key):
        """即時アンロード。SDK（接続先指定）→ REST の順に試す"""
        try:
            import lmstudio as lms
            with lms.Client(api_host=base.split("://", 1)[1]) as client:
                (client.llm.model(model_key) if model_key else client.llm.model()).unload()
            return
        except Exception as e:
            sdk_err = e
        try:
            if model_key:
                _request("POST", base + "/api/v1/models/unload", key, {"instance_id": model_key})
                return
        except Exception as e:
            sdk_err = f"{sdk_err} / {e}"
        print(f"[SFn LMStudio] アンロードに失敗: {sdk_err}")

    # ------------------------------------------------------------------ #
    def generate(self, theme, system_prompt, model_key, structured_output, generate_negative, seed,
                 max_tokens=4096, temperature=0.7, auto_unload=False, unload_delay=0,
                 timeout_seconds=300, strip_thinking=True, debug=False):
        if not theme.strip():
            return ("", "", "", "empty", False)

        if seed == -1:
            seed = random.randint(0, 0x7fffffff)

        system = system_prompt
        payload = {
            "messages": [],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed % 0x7fffffff,
            "stream": False,
        }
        base, api_key = _config()
        model_key = model_key.strip()
        if not model_key:
            # 空欄 = LM Studio 上でロード済みのモデル（取得できなければ model 省略でサーバー任せ）
            model_key = _find_loaded_model(base, api_key) or ""
            if debug:
                print(f"[SFn LMStudio] loaded model: {model_key or '(unknown)'}")
        if model_key:
            payload["model"] = model_key
        if auto_unload and unload_delay > 0:
            payload["ttl"] = unload_delay
        if structured_output:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "image_prompt",
                    "strict": True,
                    "schema": self._schema(generate_negative),
                },
            }
        else:
            system += _TEXT_FORMAT_HINT_NEG if generate_negative else _TEXT_FORMAT_HINT
        payload["messages"] = [
            {"role": "system", "content": system},
            {"role": "user", "content": theme},
        ]

        try:
            content = self._chat(base, api_key, payload, timeout_seconds, debug)
        finally:
            if auto_unload and unload_delay == 0:
                self._unload(base, api_key, model_key)

        if debug:
            print(f"[SFn LMStudio] response:\n{content}")

        ex = StringExtractPrompt()
        cleaned = ex._preprocess(content, True)
        raw_text = cleaned if strip_thinking else content

        prompt, method, success = "", "empty", False
        if cleaned:
            if structured_output:
                # 構造化出力は JSON のみを期待。壊れていれば通常の抽出にフォールバック
                found = ex._try_json(cleaned, "prompt")
                if found:
                    prompt, method, success = found, "json", True
            if not success:
                prompt, method, success = ex.extract_prompt(cleaned)

        negative = ""
        if generate_negative and cleaned:
            negative = ex.extract_negative(cleaned) or ""

        return (prompt, negative, raw_text, method, success)


NODE_CLASS_MAPPINGS = {
    "SFn_LMStudioPromptGenerator": LMStudioPromptGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SFn_LMStudioPromptGenerator": "LM Studio Prompt Generator",
}
