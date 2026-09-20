# Releases

---

## v1.2.0

### Release title
LM Studio Prompt Generator を追加 / String Extract Prompt を大幅改善

### Release notes

#### 新機能

**LM Studio Prompt Generator** — テーマから LM Studio で生成し、prompt / negative_prompt を抽出するまでを1ノードで実行
- LM Studio の Structured Output（JSON Schema）を自動付与し、出力形式の崩れを防止
- `structured_output` を False にすると `PROMPT:` / `NEGATIVE:` 形式のテキストから抽出
- 接続先は `.env` の `LMSTUDIO_BASE_URL` で指定（リモートの LM Studio も可、`.env.example` 参照）
- `model_key` を空にすると LM Studio 上のロード済みモデルを自動使用
- `auto_unload` / `unload_delay`（TTL）、`seed`、`max_tokens`、`temperature`、`timeout_seconds` に対応
- 出力は Prompt Preview にそのまま接続可能（`prompt` / `negative_prompt` / `raw_text` / `method_used` / `success`）
- 接続失敗・タイムアウト時はエラーでワークフローを停止（空プロンプトで生成が進まない）

#### 改善: String Extract Prompt
- auto の順序を `json → code_block → after_label → 前置き/後書き除去` に変更
- JSON 抽出を強化（コードブロック内・地の文中・入れ子・大文字小文字違い・途中で切れた出力に対応）
- `**Prompt:**` や `### Positive Prompt` 等のマークダウン形式ラベルに対応、Negative prompt 併記を自動除外
- 以下のモデル出力形式を吸収: Qwen3 / DeepSeek-R1（`<think>`、開始タグ無し `</think>`、閉じ忘れ）、gpt-oss、Llama 3、ChatML、Gemma、Mistral、LM Studio の reasoning マーカー
- 「The image shows…」のような説明文を前置きとして誤って削除していた問題を修正
- `json_key` のデフォルトに `positive_prompt,positive` を追加

#### バグ修正
- **String Replace**: `case_sensitive=False` かつ `count=0` のとき全置換されていた問題
- **String Split**: `occurrence` が区切り文字の長さを考慮せず重なってカウントしていた問題

---

## v1.1.0

### Release title
File Read ノードを追加

### Release notes

テキストファイルの読み込みに特化した3つのノードを追加しました。

#### 新機能

**File Read** — テキストファイル全体を読み込む
- ファイルパスを指定してテキスト全体を STRING で出力
- 行数・読み込み成功フラグを同時に出力

**File Read Line** — テキストファイルを1行ずつ読み込む
- 実行のたびに自動で次の行へ進み、末尾に達すると先頭へループ
- `sequential`（順番）/ `shuffle`（シャッフル・重複なし全件消費）の2モード
- `reset` 入力ピンで任意のタイミングに先頭へ戻せる
- `skip_empty_lines` で空行をスキップしてカウント可能

**Folder File Read** — フォルダ内のファイルを1つずつ読み込む
- 実行のたびに自動で次のファイルへ進み、末尾に達すると先頭へループ
- `sequential` / `shuffle` の2モード
- `extension_filter` でファイルの種類を絞り込み（例: `.txt,.md`）
- `sort_order` でファイルの読み込み順を指定（名前昇降順・更新日時昇降順）
- `reset` 入力ピンで任意のタイミングに先頭へ戻せる

#### 共通の改善
- **ファイル・フォルダ参照ボタン**: ノード上の「📄 ファイルを参照...」「📂 フォルダを参照...」ボタンをクリックするとOSネイティブの選択ダイアログが開き、パスを自動入力（Windows のみ）
- **encoding デフォルトを `auto` に変更**: UTF-8 BOM → UTF-8 → Shift-JIS の順で自動判別。設定不要で日本語ファイルをそのまま読める
- **ダブルクォート自動除去**: エクスプローラーからコピーしたパス（`"C:\..."` 形式）をそのまま貼り付けても動作

---

## v1.0.0

### Release title
初回リリース

### Release notes

ComfyUI 向け文字列操作カスタムノード集の初回リリースです。  
LLM の出力からプロンプトを抽出する **String Extract Prompt** を中心に、テキスト処理に役立つノードを収録しています。

#### 収録ノード

**String Extract Prompt** — LLM出力からプロンプトだけを抽出 ★
- JSON / コードブロック / ラベル付き / カンマ区切りタグ列など多様な出力形式に対応
- `<think>...</think>` ブロックの自動除去（Qwen 等）
- gpt-oss-20b のチャンネルフォーマットに対応

**Prompt Preview** — Prompt / Negative Prompt / Raw テキストを確認・中継
- 3種類のテキストをノード上のテキストエリアに整形表示
- 後続ノードへそのままスルー出力

**String Find** — 文字列の位置を検索（1始まり、見つからない場合は 0）

**String Split** — 区切り文字の前後に分割

**String Left / Mid / Right** — Excel 系の文字列切り出し

**String Default** — テキストが空のときのフォールバック

**String Replace** — 文字列の検索・置換（大文字小文字の無視、置換回数制限に対応）

**String Trim** — 前後の空白・指定文字を除去

**String Case** — 大文字・小文字の変換（upper / lower / title / capitalize / swapcase）

**String Regex Match** — 正規表現でマッチ・抽出（search / match / fullmatch / findall）
