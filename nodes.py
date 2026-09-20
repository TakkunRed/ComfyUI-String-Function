import json
import os
import random as _random
import re


def _normalize_path(path: str) -> str:
    """前後の空白・ダブルクォートを除去してパスを正規化する"""
    path = path.strip()
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        path = path[1:-1].strip()
    return path


def _read_text(file_path: str, encoding: str) -> str:
    if encoding == "auto":
        for enc in ("utf-8-sig", "utf-8", "cp932"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(file_path, "r", encoding="cp932", errors="replace") as f:
            return f.read()
    with open(file_path, "r", encoding=encoding) as f:
        return f.read()


class FileRead:
    """テキストファイル全体を読み込む"""

    _ENCODINGS = ["auto", "utf-8", "utf-8-sig", "cp932"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "encoding": (cls._ENCODINGS, {"default": "auto"}),
                "strip_newline_end": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "ファイル末尾の改行を除去する",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("text", "line_count", "success")
    FUNCTION = "read_file"
    CATEGORY = "String Function"
    DESCRIPTION = "テキストファイル全体を読み込みます"

    def read_file(self, file_path, encoding="auto", strip_newline_end=True):
        file_path = _normalize_path(file_path)
        if not file_path or not os.path.isfile(file_path):
            return ("", 0, False)
        try:
            text = _read_text(file_path, encoding)
            if strip_newline_end:
                text = text.rstrip("\r\n")
            line_count = len(text.splitlines()) if text else 0
            return (text, line_count, True)
        except Exception:
            return ("", 0, False)


class FileReadLine:
    """テキストファイルを1行ずつ読み込む（実行のたびに次の行へ進む）"""

    _MODES = ["sequential", "shuffle"]
    _ENCODINGS = ["auto", "utf-8", "utf-8-sig", "cp932"]
    _state: dict = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "mode": (cls._MODES, {"default": "sequential"}),
                "reset": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "True を受けた実行でカウンタをリセットし先頭から再開する",
                }),
                "encoding": (cls._ENCODINGS, {"default": "auto"}),
                "skip_empty_lines": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "True にすると空行をスキップしてカウント",
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "BOOLEAN")
    RETURN_NAMES = ("line_text", "line_index", "line_count", "is_last")
    FUNCTION = "read_line"
    CATEGORY = "String Function"
    DESCRIPTION = "テキストファイルを1行ずつ読み込みます。実行のたびに次の行へ進みます"

    @classmethod
    def IS_CHANGED(cls, file_path, mode="sequential", reset=False, encoding="utf-8",
                   skip_empty_lines=False, unique_id=None):
        return float("nan")

    def _load_lines(self, file_path, encoding, skip_empty):
        file_path = _normalize_path(file_path)
        if not file_path or not os.path.isfile(file_path):
            return []
        try:
            text = _read_text(file_path, encoding)
            lines = text.splitlines()
            if skip_empty:
                lines = [ln for ln in lines if ln.strip()]
            return lines
        except Exception:
            return []

    def read_line(self, file_path, mode="sequential", reset=False, encoding="auto",
                  skip_empty_lines=False, unique_id=None):
        file_path = _normalize_path(file_path)
        key = str(unique_id) if unique_id else file_path
        lines = self._load_lines(file_path, encoding, skip_empty_lines)

        if not lines:
            return ("", 0, 0, True)

        line_count = len(lines)
        st = self._state.get(key)

        if st is None or st["file_path"] != file_path:
            order = None
            if mode == "shuffle":
                order = list(range(line_count))
                _random.shuffle(order)
            st = {"file_path": file_path, "index": 0, "order": order}
            self._state[key] = st

        if reset:
            st["index"] = 0
            if mode == "shuffle":
                order = list(range(line_count))
                _random.shuffle(order)
                st["order"] = order

        idx = st["index"]

        if mode == "shuffle":
            order = st.get("order")
            if order is None or len(order) != line_count:
                order = list(range(line_count))
                _random.shuffle(order)
                st["order"] = order
                st["index"] = 0
                idx = 0

        if idx >= line_count:
            idx = 0
            st["index"] = 0

        if mode == "shuffle":
            actual_idx = st["order"][idx]
            line_text = lines[actual_idx]
            line_number = actual_idx + 1
        else:
            line_text = lines[idx]
            line_number = idx + 1

        is_last = (idx == line_count - 1)

        next_idx = idx + 1
        if next_idx >= line_count:
            st["index"] = 0
            if mode == "shuffle":
                new_order = list(range(line_count))
                _random.shuffle(new_order)
                st["order"] = new_order
        else:
            st["index"] = next_idx

        return (line_text, line_number, line_count, is_last)


class FolderFileRead:
    """フォルダ内のファイルを1つずつ読み込む（実行のたびに次のファイルへ進む）"""

    _MODES = ["sequential", "shuffle"]
    _ENCODINGS = ["auto", "utf-8", "utf-8-sig", "cp932"]
    _SORT_ORDERS = ["name_asc", "name_desc", "modified_asc", "modified_desc"]
    _state: dict = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "mode": (cls._MODES, {"default": "sequential"}),
                "reset": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "True を受けた実行でカウンタをリセットし先頭から再開する",
                }),
                "extension_filter": ("STRING", {
                    "multiline": False,
                    "default": ".txt",
                    "tooltip": "対象拡張子（カンマ区切り例: .txt,.md）。空白で全ファイル",
                }),
                "encoding": (cls._ENCODINGS, {"default": "auto"}),
                "sort_order": (cls._SORT_ORDERS, {
                    "default": "name_asc",
                    "tooltip": "sequential モード時のファイル順序",
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT", "BOOLEAN")
    RETURN_NAMES = ("text", "file_name", "file_path_out", "file_index", "file_count", "is_last")
    FUNCTION = "read_folder_file"
    CATEGORY = "String Function"
    DESCRIPTION = "フォルダ内のファイルを1つずつ読み込みます。実行のたびに次のファイルへ進みます"

    @classmethod
    def IS_CHANGED(cls, folder_path, mode="sequential", reset=False, extension_filter=".txt",
                   encoding="utf-8", sort_order="name_asc", unique_id=None):
        return float("nan")

    def _get_file_list(self, folder_path, extension_filter, sort_order):
        folder_path = _normalize_path(folder_path)
        if not folder_path or not os.path.isdir(folder_path):
            return []
        exts = set()
        if extension_filter.strip():
            for e in extension_filter.split(","):
                e = e.strip()
                if e and not e.startswith("."):
                    e = "." + e
                if e:
                    exts.add(e.lower())
        files = []
        for fname in os.listdir(folder_path):
            fpath = os.path.join(folder_path, fname)
            if not os.path.isfile(fpath):
                continue
            if exts:
                _, ext = os.path.splitext(fname)
                if ext.lower() not in exts:
                    continue
            files.append(fpath)
        if sort_order == "name_asc":
            files.sort(key=lambda p: os.path.basename(p).lower())
        elif sort_order == "name_desc":
            files.sort(key=lambda p: os.path.basename(p).lower(), reverse=True)
        elif sort_order == "modified_asc":
            files.sort(key=lambda p: os.path.getmtime(p))
        elif sort_order == "modified_desc":
            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files

    def read_folder_file(self, folder_path, mode="sequential", reset=False,
                         extension_filter=".txt", encoding="auto",
                         sort_order="name_asc", unique_id=None):
        folder_path = _normalize_path(folder_path)
        key = str(unique_id) if unique_id else folder_path
        files = self._get_file_list(folder_path, extension_filter, sort_order)

        if not files:
            return ("", "", "", 0, 0, True)

        file_count = len(files)
        st = self._state.get(key)

        if st is None or st["folder_path"] != folder_path:
            order = None
            if mode == "shuffle":
                order = list(range(file_count))
                _random.shuffle(order)
            st = {"folder_path": folder_path, "index": 0, "order": order}
            self._state[key] = st

        if reset:
            st["index"] = 0
            if mode == "shuffle":
                order = list(range(file_count))
                _random.shuffle(order)
                st["order"] = order

        idx = st["index"]

        if mode == "shuffle":
            order = st.get("order")
            if order is None or len(order) != file_count:
                order = list(range(file_count))
                _random.shuffle(order)
                st["order"] = order
                st["index"] = 0
                idx = 0

        if idx >= file_count:
            idx = 0
            st["index"] = 0

        if mode == "shuffle":
            actual_idx = st["order"][idx]
            fpath = files[actual_idx]
            file_number = actual_idx + 1
        else:
            fpath = files[idx]
            file_number = idx + 1

        is_last = (idx == file_count - 1)

        try:
            text = _read_text(fpath, encoding)
        except Exception:
            text = ""

        file_name = os.path.basename(fpath)

        next_idx = idx + 1
        if next_idx >= file_count:
            st["index"] = 0
            if mode == "shuffle":
                new_order = list(range(file_count))
                _random.shuffle(new_order)
                st["order"] = new_order
        else:
            st["index"] = next_idx

        return (text, file_name, fpath, file_number, file_count, is_last)


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
                idx = split_at + len(delimiter)
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
                parts = re.split(re.escape(old), text, maxsplit=count, flags=flags) if count else [text]
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

    # auto モードで試みる構造抽出（「見つからない」= None を返せる手法のみ）
    # json を code_block より先に試す: ```json ... ``` の中身をそのまま返さないため
    _AUTO_ORDER = ["json", "code_block", "after_label"]

    _THINK_TAGS = r"(?:think|thinking|thought|reasoning)"
    _NON_PROMPT_LANGS = {"json", "yaml", "yml", "xml", "toml", "python", "py", "js", "javascript"}
    _POS_PREFIX = (
        r"positive|final|image|generated|main|full|revised|refined|english|japanese|detailed|"
        r"ポジティブ|最終|英語|日本語|画像生成"
    )

    _NEG_RE = re.compile(
        r"^[ \t]*(?:#{1,6}[ \t]*|[-*>][ \t]+)?(?:\*\*|__)?"
        r"(?:negative(?:[ _-]?prompt)?|ネガティブ(?:プロンプト)?|除外(?:プロンプト)?)"
        r"(?:\*\*|__)?[ \t]*[:：]",
        re.IGNORECASE | re.MULTILINE,
    )
    _LEAD_LABEL_RE = re.compile(
        r"^(?:#{1,6}[ \t]*)?(?:\*\*|__)?"
        r"(?:(?:" + _POS_PREFIX + r")[ \t]+)?(?:prompt|プロンプト)"
        r"(?:\*\*|__)?[ \t]*[:：][ \t]*(?:\*\*|__)?[ \t]*",
        re.IGNORECASE,
    )
    _PREAMBLE_RE = re.compile(
        "(?:" + "|".join([
            r"(?:sure|of course|certainly|absolutely|okay|ok|alright|great)[!,.]\s*",
            r"here(?:'s| is| are)\b[^:：\n]{0,80}[:：]\s*",
            r"here(?:'s| is| are)\b[^\n]{0,80}(?:prompt|description|caption)[^\n]{0,40}\n+\s*",
            r"(?:based on|according to) (?:the |my |your )?"
            r"(?:image|analysis|input|request|description|photo)[^,\n:：]*[,、:：]\s*",
            r"(?:i(?:'ve| have)? (?:created|generated|written|crafted|prepared)|"
            r"let me (?:create|write|craft|generate))[^:：\n]{0,80}[:：]\s*",
            r"(?:以下(?:が|は|に|の)?|次(?:が|は|の)|下記(?:が|は|の)?)"
            r"[^。\n:：]{0,40}(?:プロンプト|prompt)[^。\n:：]{0,30}[。:：]\s*",
            r"(?:はい|承知(?:しました|いたしました)|了解(?:しました)?|かしこまりました)[、,。!！]?\s*",
        ]) + ")",
        re.IGNORECASE,
    )
    _POSTAMBLE_RE = re.compile(
        r"^(?:let me know|feel free|i hope|hope this|if you(?:'d| would| want| need| like)|"
        r"would you like|do you want|please let|this prompt|these (?:tags|keywords)|"
        r"note\s*[:：]|explanation|the above|you can (?:adjust|modify|tweak)|"
        r"ご要望|必要であれば|お気軽|ご希望|この(?:プロンプト|ように)|以上)",
        re.IGNORECASE,
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "mode": (cls.MODES, {
                    "default": "auto",
                    "tooltip": (
                        "auto=構造抽出→前置き/後書き除去を順に試す / code_block=```抽出 / "
                        "json=JSONフィールド抽出 / after_label=ラベル後テキスト / "
                        "strip_preamble=前置き・後書き除去 / most_commas=カンマ最多段落 / "
                        "first_line=最初の行 / raw=そのまま"
                    ),
                }),
            },
            "optional": {
                "json_key": ("STRING", {
                    "multiline": False,
                    "default": "prompt,positive_prompt,positive,description,text,content",
                    "tooltip": (
                        "json モード時に探すキー名。カンマ区切りで優先順に複数指定可。"
                        "大文字小文字・空白/_/- の違いは無視し、入れ子のJSONも探索する"
                    ),
                }),
                "label_names": ("STRING", {
                    "multiline": False,
                    "default": "Prompt,プロンプト,Description,Output,Result",
                    "tooltip": "after_label モード時に認識するラベル名。カンマ区切りで優先順",
                }),
                "strip_think_blocks": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "<think>...</think> 等の思考ブロックを除去する (Qwen3 / DeepSeek-R1 等)",
                }),
                "fallback_to_raw": ("BOOLEAN", {
                    "default": True,
                    "tooltip": (
                        "auto モードで確信を持てなかったとき:"
                        " True=前置き除去済みテキストを返す / False=空を返す"
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
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # LM Studio: 思考部と本文の境界マーカー。最後の END 以降のみ採用
        ends = list(re.finditer(r"LM_STUDIO_INTERNAL_LSEP_SYNTHETIC_REASONING_END_[0-9a-fA-F]*_*", text))
        if ends:
            text = text[ends[-1].end():]
        text = re.sub(r"LM_STUDIO_INTERNAL_LSEP_SYNTHETIC_REASONING_START_[0-9a-fA-F]*_*", "", text)

        # gpt-oss: final チャンネルだけを採用（複数あれば最後）。無ければ analysis 等を除去
        finals = list(re.finditer(
            r"<\|channel\|>final<\|message\|>(.*?)(?=<\|(?:end|return|start|channel)\|>|\Z)",
            text, re.DOTALL | re.IGNORECASE,
        ))
        if finals:
            text = finals[-1].group(1)
        else:
            text = re.sub(
                r"<\|channel\|>(?:analysis|commentary)<\|message\|>"
                r".*?(?=<\|(?:end|return|start|channel)\|>|\Z)",
                "", text, flags=re.DOTALL | re.IGNORECASE,
            )

        if strip_think:
            t = self._THINK_TAGS
            text = re.sub(rf"<({t})>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
            # 開始タグ無しの </think>（テンプレート側で <think> が付与済みのモデル）
            closers = list(re.finditer(rf"</{t}>", text, re.IGNORECASE))
            if closers:
                text = text[closers[-1].end():]
            # 閉じられていない <think>（出力が途中で切れた場合）
            text = re.sub(rf"<{t}>.*\Z", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<unused94>.*?<unused95>", "", text, flags=re.DOTALL)  # Gemma

        # チャットテンプレートの残骸（ロール名ごと除去）
        text = re.sub(r"<\|start_header_id\|>[^<]*<\|end_header_id\|>", "", text)
        text = re.sub(r"<\|(?:im_start|start)\|>\s*assistant[ \t]*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<start_of_turn>\s*(?:model|user)[ \t]*\n?", "", text)
        if "[/INST]" in text:
            text = text.rsplit("[/INST]", 1)[1]
        text = re.sub(r"<\|[^|>]+\|>", "", text)
        text = re.sub(r"</?s>|<(?:start|end)_of_turn>|<(?:bos|eos|pad|unk)>|\[INST\]", "", text)
        return text.strip()

    # ------------------------------------------------------------------ #
    # 共通ヘルパー
    # ------------------------------------------------------------------ #
    @staticmethod
    def _strip_wrappers(s):
        """前後の引用符・強調記号・区切り線を除去する"""
        pairs = [('"', '"'), ("'", "'"), ("“", "”"), ("「", "」"), ("『", "』"), ("`", "`")]
        for _ in range(4):
            prev = s
            s = s.strip()
            s = re.sub(r"^(?:-{3,}|\*{3,}|_{3,})[ \t]*\n", "", s)
            s = re.sub(r"\n[ \t]*(?:-{3,}|\*{3,}|_{3,})$", "", s)
            if s.startswith("**") and s.endswith("**") and len(s) > 4:
                s = s[2:-2]
            for o, c in pairs:
                if len(s) >= 2 and s[0] == o and s[-1] == c:
                    # 引用符が両端だけのときのみ外す ("a", "b" のような列は触らない)
                    if o == c and s.count(o) != 2:
                        continue
                    s = s[1:-1]
                    break
            if s == prev:
                break
        return s.strip()

    def _finalize(self, s):
        """先頭の Prompt: ラベル・後続の Negative prompt・前後の装飾を落とす"""
        s = self._strip_wrappers(s)
        s = self._LEAD_LABEL_RE.sub("", s, count=1)
        m = self._NEG_RE.search(s)
        if m and m.start() > 0:
            s = s[:m.start()]
        return self._strip_wrappers(s)

    def _strip_preamble_text(self, text):
        current = text.strip()
        for _ in range(5):
            m = self._PREAMBLE_RE.match(current)
            if not m or not m.end():
                break
            current = current[m.end():].strip()
        return current

    def _split_paragraphs(self, text):
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    def _strip_postamble(self, paras):
        paras = list(paras)
        while len(paras) > 1 and self._POSTAMBLE_RE.match(paras[-1]):
            paras.pop()
        return paras

    @staticmethod
    def _is_heading(p):
        if "\n" in p or len(p) > 40:
            return False
        return p.endswith((":", "：")) or p.startswith("#") or (p.startswith("**") and p.endswith("**"))

    def _candidate_paragraphs(self, text):
        """前置き・後書き・見出し・ネガティブ段落を除いた段落リスト"""
        paras = self._strip_postamble(self._split_paragraphs(self._strip_preamble_text(text)))
        non_neg = [p for p in paras if not self._NEG_RE.match(p)]
        paras = non_neg or paras
        if len(paras) > 1:
            paras = [p for p in paras if not self._is_heading(p)] or paras
        return paras

    # ------------------------------------------------------------------ #
    # 抽出戦略
    # ------------------------------------------------------------------ #
    def _try_code_block(self, text):
        blocks = [(m.group(1).lower(), m.group(2))
                  for m in re.finditer(r"```[ \t]*([\w+.#-]*)[ \t]*\n(.*?)```", text, re.DOTALL)]
        blocks += [("", m.group(1)) for m in re.finditer(r"```(?![ \t]*\n)([^`\n][^`]*?)```", text, re.DOTALL)]
        # 閉じ忘れ（出力が途中で切れた場合）
        m = re.search(r"```[ \t]*([\w+.#-]*)[ \t]*\n(.*)\Z", text, re.DOTALL)
        if m and not blocks:
            blocks.append((m.group(1).lower(), m.group(2)))
        for lang, body in blocks:
            if lang in self._NON_PROMPT_LANGS:
                continue
            body = self._finalize(body)
            if body:
                return body
        m = re.fullmatch(r"`([^`\n]+)`", text.strip())
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _norm_key(k):
        return re.sub(r"[\s_\-]+", "", str(k)).lower()

    def _json_value(self, obj, nkey):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if self._norm_key(k) == nkey:
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                    if isinstance(v, list) and v and all(isinstance(i, str) for i in v):
                        return ", ".join(i.strip() for i in v if i.strip()) or None
            for v in obj.values():
                r = self._json_value(v, nkey)
                if r:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = self._json_value(v, nkey)
                if r:
                    return r
        return None

    def _try_json(self, text, json_key):
        keys = [k.strip() for k in json_key.split(",") if k.strip()]
        if not keys:
            return None

        # 文中の全 JSON オブジェクトを走査（波括弧を含む地の文があっても壊れない）
        decoder = json.JSONDecoder()
        objs, pos = [], 0
        while True:
            start = text.find("{", pos)
            if start == -1:
                break
            try:
                obj, end = decoder.raw_decode(text, start)
                objs.append(obj)
                pos = end
            except json.JSONDecodeError:
                pos = start + 1
        for k in keys:
            nk = self._norm_key(k)
            for obj in objs:
                val = self._json_value(obj, nk)
                if val:
                    return val

        # 不正な JSON（文字列内の生改行・途中で切れた出力など）は正規表現で拾う
        for k in keys:
            m = re.search(r'"' + re.escape(k) + r'"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.IGNORECASE)
            if m:
                try:
                    val = json.loads('"' + m.group(1) + '"', strict=False)
                except json.JSONDecodeError:
                    val = m.group(1)
                if val.strip():
                    return val.strip()
        return None

    def _try_after_label(self, text, label_names):
        labels = [l.strip() for l in label_names.split(",") if l.strip()]
        lines = text.split("\n")
        for label in labels:
            pat = re.compile(
                r"^[ \t]*(?:#{1,6}[ \t]*|[-*>•][ \t]+|\d+[.)][ \t]+)?(?:\*\*|__)?"
                r"(?:(?:" + self._POS_PREFIX + r")[ \t]+)?" + re.escape(label) +
                r"(?:\*\*|__)?[ \t]*(?:(?P<sep>[:：]|[ \t][-–—][ \t])(?:\*\*|__)?[ \t]*)?(?P<rest>.*)$",
                re.IGNORECASE,
            )
            for i, line in enumerate(lines):
                m = pat.match(line)
                if not m:
                    continue
                rest = m.group("rest").strip()
                if not m.group("sep") and rest:
                    continue  # "Prompts are ..." のような普通の文
                collected = [rest] if rest else []
                j = i + 1
                if not collected:  # 見出し形式: 次の非空行から本文
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                if j < len(lines) and not collected and lines[j].strip().startswith("```"):
                    j += 1
                    while j < len(lines) and not lines[j].strip().startswith("```"):
                        collected.append(lines[j])
                        j += 1
                else:
                    while j < len(lines) and lines[j].strip() and not self._NEG_RE.match(lines[j]):
                        if lines[j].strip().startswith("```"):
                            break
                        collected.append(lines[j])
                        j += 1
                result = self._finalize("\n".join(collected))
                if result:
                    return result
        return None

    def _try_strip_preamble(self, text):
        paras = self._candidate_paragraphs(text)
        result = self._finalize("\n\n".join(paras)) if paras else ""
        return result or None

    def _try_most_commas(self, text):
        paras = self._candidate_paragraphs(text)
        if not paras:
            paras = [l.strip() for l in text.splitlines() if l.strip()]
        if not paras:
            return None
        best = max(paras, key=lambda p: p.count(",") + p.count("，"))
        if best.count(",") + best.count("，") < 1:
            return None
        return self._finalize(best) or None

    def _try_first_line(self, text):
        for line in self._strip_preamble_text(text).splitlines():
            line = self._finalize(line)
            if line:
                return line
        return None

    def _try_heuristic(self, text):
        """構造が無い出力向け: 前置き・後書きを除去して本文を推定する。(result, method, confident)"""
        paras = self._candidate_paragraphs(text)
        if not paras:
            return None
        if len(paras) == 1:
            res = self._finalize(paras[0])
            if not res:
                return None
            return (res, "plain" if res == text.strip() else "strip_preamble", True)
        best = max(paras, key=lambda p: p.count(",") + p.count("，"))
        if best.count(",") + best.count("，") >= 2:
            res = self._finalize(best)
            if res:
                return (res, "most_commas", True)
        res = self._finalize("\n\n".join(paras))
        return (res, "raw_fallback", False) if res else None

    def extract_negative(self, cleaned, json_key="negative_prompt,negative,neg_prompt",
                         label_names="Negative Prompt,Negative,ネガティブプロンプト,ネガティブ,除外プロンプト"):
        """前処理済みテキストから negative prompt を取り出す。無ければ None"""
        return self._try_json(cleaned, json_key) or self._try_after_label(cleaned, label_names)

    # ------------------------------------------------------------------ #
    # メイン
    # ------------------------------------------------------------------ #
    def extract_prompt(self, text, mode="auto", json_key="prompt,positive_prompt,positive,description,text,content",
                       label_names="Prompt,プロンプト,Description,Output,Result",
                       strip_think_blocks=True, fallback_to_raw=True):

        cleaned = self._preprocess(text or "", strip_think_blocks)
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

        for name in self._AUTO_ORDER:
            result = strategy_map[name]()
            if result:
                return (result, name, True)

        found = self._try_heuristic(cleaned)
        if found:
            result, method, confident = found
            if confident:
                return (result, method, True)
            if fallback_to_raw:
                return (result, method, False)
            return ("", "none", False)

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
    "SFn_FileRead":           FileRead,
    "SFn_FileReadLine":       FileReadLine,
    "SFn_FolderFileRead":     FolderFileRead,
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
    "SFn_FileRead":           "File Read",
    "SFn_FileReadLine":       "File Read Line",
    "SFn_FolderFileRead":     "Folder File Read",
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
