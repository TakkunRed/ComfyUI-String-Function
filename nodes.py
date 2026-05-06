class StringFind:
    """文字列内で特定の文字列が何文字目にあるかを返す (1始まり、見つからない場合は 0)"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "search": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "start_pos": ("INT", {"default": 1, "min": 1, "max": 99999,
                                      "tooltip": "検索を開始する位置 (1始まり)"}),
                "occurrence": ("INT", {"default": 1, "min": 1, "max": 999,
                                       "tooltip": "何番目の出現を検索するか"}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("position",)
    FUNCTION = "find_string"
    CATEGORY = "String Function"
    DESCRIPTION = "文字列内の検索文字列の位置を返します (1始まり、見つからない場合は 0)"

    def find_string(self, text, search, start_pos=1, occurrence=1):
        if not search:
            return (0,)
        idx = start_pos - 1
        count = 0
        while True:
            found = text.find(search, idx)
            if found == -1:
                return (0,)
            count += 1
            if count == occurrence:
                return (found + 1,)
            idx = found + 1


class StringSplit:
    """特定の文字列で前後に分割して返す"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "delimiter": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "occurrence": ("INT", {"default": 1, "min": 1, "max": 999,
                                       "tooltip": "何番目の区切り文字で分割するか (use_last が True のときは無視)"}),
                "use_last": ("BOOLEAN", {"default": False,
                                         "tooltip": "True にすると最後に出現した区切り文字で分割する"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("before", "after")
    FUNCTION = "split_string"
    CATEGORY = "String Function"
    DESCRIPTION = "区切り文字の前後で文字列を分割します"

    def split_string(self, text, delimiter, occurrence=1, use_last=False):
        if not delimiter:
            return (text, "")
        if use_last:
            split_at = text.rfind(delimiter)
            if split_at == -1:
                return (text, "")
        else:
            idx = 0
            split_at = -1
            for _ in range(occurrence):
                split_at = text.find(delimiter, idx)
                if split_at == -1:
                    return (text, "")
                idx = split_at + 1
        before = text[:split_at]
        after = text[split_at + len(delimiter):]
        return (before, after)


class StringLeft:
    """左から n 文字を返す (Excel の LEFT 関数相当)"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "num_chars": ("INT", {"default": 1, "min": 0, "max": 99999}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "left"
    CATEGORY = "String Function"
    DESCRIPTION = "左から指定した文字数を返します"

    def left(self, text, num_chars):
        return (text[:num_chars],)


class StringRight:
    """右から n 文字を返す (Excel の RIGHT 関数相当)"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "num_chars": ("INT", {"default": 1, "min": 0, "max": 99999}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "right"
    CATEGORY = "String Function"
    DESCRIPTION = "右から指定した文字数を返します"

    def right(self, text, num_chars):
        if num_chars == 0:
            return ("",)
        return (text[-num_chars:],)


class StringMid:
    """指定位置から n 文字を返す (Excel の MID 関数相当)"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "start_pos": ("INT", {"default": 1, "min": 1, "max": 99999,
                                      "tooltip": "開始位置 (1始まり)"}),
                "num_chars": ("INT", {"default": 1, "min": 0, "max": 99999}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "mid"
    CATEGORY = "String Function"
    DESCRIPTION = "指定した位置から指定した文字数を返します"

    def mid(self, text, start_pos, num_chars):
        idx = max(0, start_pos - 1)
        return (text[idx: idx + num_chars],)


class StringDefault:
    """文字列が空のとき、代わりの文字列を返す"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "default_value": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "trim_before_check": ("BOOLEAN", {"default": False,
                                                   "tooltip": "チェック前に前後の空白を除去する"}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("result", "was_empty")
    FUNCTION = "default_string"
    CATEGORY = "String Function"
    DESCRIPTION = "テキストが空のとき default_value を返します"

    def default_string(self, text, default_value, trim_before_check=False):
        check = text.strip() if trim_before_check else text
        if check == "":
            return (default_value, True)
        return (text, False)


class StringReplace:
    """文字列の置換"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "old": ("STRING", {"multiline": False, "default": ""}),
                "new": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "count": ("INT", {"default": -1, "min": -1, "max": 99999,
                                  "tooltip": "置換する最大回数。-1 は全て置換"}),
                "case_sensitive": ("BOOLEAN", {"default": True,
                                               "tooltip": "False にすると大文字小文字を無視して置換"}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("result", "replace_count")
    FUNCTION = "replace_string"
    CATEGORY = "String Function"
    DESCRIPTION = "文字列を検索して置換します"

    def replace_string(self, text, old, new, count=-1, case_sensitive=True):
        if not old:
            return (text, 0)
        if case_sensitive:
            actual_count = text.count(old) if count == -1 else min(text.count(old), count)
            result = text.replace(old, new, count if count != -1 else -1)
        else:
            import re
            flags = re.IGNORECASE
            parts = re.split(re.escape(old), text, flags=flags)
            actual_count = len(parts) - 1
            if count != -1:
                parts = re.split(re.escape(old), text, maxsplit=count, flags=flags)
                actual_count = min(actual_count, count)
            result = new.join(parts)
        return (result, actual_count)


class StringTrim:
    """前後の空白・指定文字を除去する"""

    TRIM_MODES = ["both", "left", "right"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "mode": (cls.TRIM_MODES, {"default": "both",
                                          "tooltip": "both=前後, left=左のみ, right=右のみ"}),
            },
            "optional": {
                "chars": ("STRING", {"multiline": False, "default": "",
                                     "tooltip": "除去する文字を列挙。空白のままにすると空白文字を除去"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "trim_string"
    CATEGORY = "String Function"
    DESCRIPTION = "文字列の前後から空白または指定文字を除去します"

    def trim_string(self, text, mode="both", chars=""):
        chars_arg = chars if chars else None
        if mode == "left":
            return (text.lstrip(chars_arg),)
        if mode == "right":
            return (text.rstrip(chars_arg),)
        return (text.strip(chars_arg),)


class StringCase:
    """大文字・小文字の変換"""

    CASE_MODES = ["upper", "lower", "title", "capitalize", "swapcase"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "mode": (cls.CASE_MODES, {"default": "upper"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "change_case"
    CATEGORY = "String Function"
    DESCRIPTION = "文字列の大文字・小文字を変換します"

    def change_case(self, text, mode):
        ops = {
            "upper": str.upper,
            "lower": str.lower,
            "title": str.title,
            "capitalize": str.capitalize,
            "swapcase": str.swapcase,
        }
        return (ops[mode](text),)


class StringRegexMatch:
    """正規表現でマッチ・抽出・検索"""

    MODES = ["match", "search", "findall", "fullmatch"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "pattern": ("STRING", {"multiline": False, "default": ""}),
                "mode": (cls.MODES, {"default": "search",
                                     "tooltip": "search=どこでも検索, match=先頭から, fullmatch=全体, findall=全件取得"}),
            },
            "optional": {
                "group": ("INT", {"default": 0, "min": 0, "max": 99,
                                  "tooltip": "取得するグループ番号 (0=マッチ全体, 1以降=キャプチャグループ)。findall モードでは無視"}),
                "ignore_case": ("BOOLEAN", {"default": False}),
                "multiline": ("BOOLEAN", {"default": False,
                                          "tooltip": "True にすると ^ $ が各行の先頭・末尾にマッチ"}),
                "join_str": ("STRING", {"multiline": False, "default": ", ",
                                        "tooltip": "findall モードで複数結果を結合する区切り文字"}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "INT")
    RETURN_NAMES = ("result", "matched", "match_count")
    FUNCTION = "regex_match"
    CATEGORY = "String Function"
    DESCRIPTION = "正規表現でテキストを検索・抽出します"

    def regex_match(self, text, pattern, mode="search", group=0,
                    ignore_case=False, multiline=False, join_str=", "):
        import re
        if not pattern:
            return ("", False, 0)

        flags = 0
        if ignore_case:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.MULTILINE

        try:
            if mode == "findall":
                results = re.findall(pattern, flags=flags, string=text)
                flat = [m if isinstance(m, str) else join_str.join(m) for m in results]
                return (join_str.join(flat), len(flat) > 0, len(flat))

            fn = {"search": re.search, "match": re.match, "fullmatch": re.fullmatch}[mode]
            m = fn(pattern, text, flags)
            if m is None:
                return ("", False, 0)
            try:
                extracted = m.group(group)
            except IndexError:
                extracted = m.group(0)
            return (extracted if extracted is not None else "", True, 1)
        except re.error as e:
            return (f"[regex error: {e}]", False, 0)


class StringExtractPrompt:
    """LLM出力からプロンプト文字列だけを抽出する"""

    MODES = [
        "auto",
        "code_block",
        "json",
        "after_label",
        "strip_preamble",
        "most_commas",
        "first_line",
        "raw",
    ]

    # auto モードで試みる手法（「見つからない」= None を返せる手法のみ）
    # strip_preamble / first_line / raw は「必ず何か返る」ので auto では使わない
    _AUTO_ORDER = ["code_block", "json", "after_label", "most_commas"]

    # 前置き文パターン（英語・日本語）— 複数回適用して多段階前置きを除去
    _PREAMBLE_RE = None

    @classmethod
    def _preamble_re(cls):
        import re
        if cls._PREAMBLE_RE is None:
            patterns = [
                r"^here(?:'s| is)\s+(?:(?:a|the)\s+)?(?:\w+\s+){0,3}(?:prompt|プロンプト)\s*[:\-]\s*",
                r"^here(?:'s| is)\b[^:\n]{0,60}[:\-]\s*",
                r"^based on (?:the |my |your )?(?:image|analysis|input|request)[^,\n]*[,、]\s*",
                r"^(?:i (?:can see|observe|notice|suggest|recommend|will provide|have created)|"
                r"the (?:image|photo|picture|scene|following) (?:shows?|depicts?|features?|is|captures?))"
                r"[^.。\n]*[.。]\s*",
                r"^(?:以下|次|下記)(?:が|は|に)?(?:プロンプト|prompt)[^。\n]*[。:：]\s*",
                r"^(?:sure|of course|certainly|absolutely)[!,.]?\s*",
                r"^PROMPT:\s*",
            ]
            cls._PREAMBLE_RE = re.compile(
                "(?:" + "|".join(patterns) + ")", re.IGNORECASE
            )
        return cls._PREAMBLE_RE

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "mode": (cls.MODES, {
                    "default": "auto",
                    "tooltip": (
                        "auto=構造抽出を順に試す / code_block=```抽出 / "
                        "json=JSONフィールド抽出 / after_label=ラベル後テキスト / "
                        "strip_preamble=前置き除去 / most_commas=カンマ最多行 / "
                        "first_line=最初の行 / raw=そのまま"
                    ),
                }),
            },
            "optional": {
                "json_key": ("STRING", {
                    "multiline": False,
                    "default": "prompt,description,text,content",
                    "tooltip": "json モード時に探すキー名。カンマ区切りで優先順に複数指定可",
                }),
                "label_names": ("STRING", {
                    "multiline": False,
                    "default": "Prompt,プロンプト,Description,Output,Result",
                    "tooltip": "after_label モード時に認識するラベル名。カンマ区切り",
                }),
                "strip_think_blocks": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "<think>...</think> ブロックを除去する (Qwen等)",
                }),
                "fallback_to_raw": ("BOOLEAN", {
                    "default": True,
                    "tooltip": (
                        "auto モードで全手法が失敗したとき:"
                        " True=クリーン済みテキスト全体を返す / False=空を返す"
                    ),
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("prompt", "method_used", "success")
    FUNCTION = "extract_prompt"
    CATEGORY = "String Function"
    DESCRIPTION = "LLMの出力テキストから画像生成プロンプトだけを抽出します"

    # ------------------------------------------------------------------ #
    # 前処理
    # ------------------------------------------------------------------ #
    def _preprocess(self, text, strip_think):
        import re
        if strip_think:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # gpt-oss-20b チャンネルフォーマット
        channel_match = re.search(
            r"<\|channel\|>final<\|message\|>(.*?)(?:<\|end\|>|$)",
            text, re.DOTALL | re.IGNORECASE
        )
        if channel_match:
            text = channel_match.group(1).strip()
        # 残留特殊トークン除去
        text = re.sub(r"<\|[^|>]+\|>", "", text)
        return text.strip()

    # ------------------------------------------------------------------ #
    # 抽出戦略
    # ------------------------------------------------------------------ #
    def _try_code_block(self, text):
        import re
        m = re.search(r"```(?:[^\n]*\n)?(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        m = re.search(r"`([^`]+)`", text)
        if m:
            return m.group(1).strip()
        return None

    def _try_json(self, text, json_key):
        import re, json
        keys = [k.strip() for k in json_key.split(",") if k.strip()]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        for k in keys:
            if k in obj and isinstance(obj[k], str) and obj[k].strip():
                val = obj[k].strip()
                val = re.sub(r"^[A-Za-zぁ-ん一-龯]+\s*[:：]\s*", "", val).strip()
                return val if val else None
        return None

    def _try_after_label(self, text, label_names):
        import re
        labels = [re.escape(l.strip()) for l in label_names.split(",") if l.strip()]
        pattern = r"(?:^|\n)(?:" + "|".join(labels) + r")\s*[:：\-]\s*(.+?)(?:\n\n|\Z)"
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
        return None

    def _try_strip_preamble(self, text):
        pat = self._preamble_re()
        current = text.strip()
        for _ in range(5):
            next_text = pat.sub("", current, count=1).strip()
            if next_text == current:
                break
            current = next_text
        return current if current and current != text.strip() else None

    def _try_most_commas(self, text):
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [l.strip() for l in text.splitlines() if l.strip()]
        if not paragraphs:
            return None
        best = max(paragraphs, key=lambda p: p.count(","))
        return best if best.count(",") >= 1 else None

    def _try_first_line(self, text):
        for line in text.splitlines():
            if line.strip():
                return line.strip()
        return None

    # ------------------------------------------------------------------ #
    # メイン
    # ------------------------------------------------------------------ #
    def extract_prompt(self, text, mode="auto", json_key="prompt,description,text,content",
                       label_names="Prompt,プロンプト,Description,Output,Result",
                       strip_think_blocks=True, fallback_to_raw=True):

        cleaned = self._preprocess(text, strip_think_blocks)
        if not cleaned:
            return ("", "empty", False)

        strategy_map = {
            "code_block":    lambda: self._try_code_block(cleaned),
            "json":          lambda: self._try_json(cleaned, json_key),
            "after_label":   lambda: self._try_after_label(cleaned, label_names),
            "strip_preamble":lambda: self._try_strip_preamble(cleaned),
            "most_commas":   lambda: self._try_most_commas(cleaned),
            "first_line":    lambda: self._try_first_line(cleaned),
            "raw":           lambda: cleaned,
        }

        if mode != "auto":
            # 個別モード指定: fallback_to_raw は関係なく指定手法のみ実行
            fn = strategy_map.get(mode)
            result = fn() if fn else None
            if result:
                return (result, mode, True)
            return ("", mode, False)

        # auto モード: _AUTO_ORDER の手法のみ試みる
        # （strip_preamble / first_line / raw は「必ず何か返る」ので含めない）
        for name in self._AUTO_ORDER:
            result = strategy_map[name]()
            if result:
                return (result, name, True)

        # 全手法失敗 → fallback_to_raw で制御
        if fallback_to_raw:
            return (cleaned, "raw_fallback", False)
        return ("", "none", False)


class PromptPreview:
    """Prompt / Negative Prompt / Raw LLM Text を1つのテキストエリアに整形して表示し、後続ノードへ渡す"""

    SEP = "─" * 22

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "prompt":          ("STRING", {"forceInput": True}),
                "negative_prompt": ("STRING", {"forceInput": True}),
                "raw_text":        ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES  = ("STRING", "STRING", "STRING")
    RETURN_NAMES  = ("prompt", "negative_prompt", "raw_text")
    FUNCTION      = "preview"
    OUTPUT_NODE   = True
    CATEGORY      = "String Function"
    DESCRIPTION   = "Prompt / Negative Prompt / Raw LLM Text を表示し、後続ノードへ渡します"

    def preview(self, prompt="", negative_prompt="", raw_text=""):
        s = self.SEP
        display = (
            f"[ Prompt ]\n{prompt or '(empty)'}\n\n"
            f"{s}\n"
            f"[ Negative Prompt ]\n{negative_prompt or '(empty)'}\n\n"
            f"{s}\n"
            f"[ Raw LLM Output ]\n{raw_text or '(empty)'}"
        )
        return {
            "ui":     {"text": [display]},
            "result": (prompt, negative_prompt, raw_text),
        }


NODE_CLASS_MAPPINGS = {
    "SFn_StringFind":         StringFind,
    "SFn_StringSplit":        StringSplit,
    "SFn_StringLeft":         StringLeft,
    "SFn_StringRight":        StringRight,
    "SFn_StringMid":          StringMid,
    "SFn_StringDefault":      StringDefault,
    "SFn_StringReplace":      StringReplace,
    "SFn_StringTrim":         StringTrim,
    "SFn_StringCase":         StringCase,
    "SFn_StringRegexMatch":   StringRegexMatch,
    "SFn_StringExtractPrompt":StringExtractPrompt,
    "SFn_PromptPreview":      PromptPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SFn_StringFind":         "String Find",
    "SFn_StringSplit":        "String Split",
    "SFn_StringLeft":         "String Left",
    "SFn_StringRight":        "String Right",
    "SFn_StringMid":          "String Mid",
    "SFn_StringDefault":      "String Default",
    "SFn_StringReplace":      "String Replace",
    "SFn_StringTrim":         "String Trim",
    "SFn_StringCase":         "String Case",
    "SFn_StringRegexMatch":   "String Regex Match",
    "SFn_StringExtractPrompt":"String Extract Prompt",
    "SFn_PromptPreview":      "Prompt Preview",
}
