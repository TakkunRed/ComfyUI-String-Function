from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from . import prompt_generator as _pg

NODE_CLASS_MAPPINGS = {**NODE_CLASS_MAPPINGS, **_pg.NODE_CLASS_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**NODE_DISPLAY_NAME_MAPPINGS, **_pg.NODE_DISPLAY_NAME_MAPPINGS}

WEB_DIRECTORY = "./web"

try:
    from server import PromptServer
    from aiohttp import web
    import asyncio
    import subprocess

    # Application.Run でメッセージループを立ち上げ、TopMost フォームをオーナーにして
    # ダイアログを前面に表示する。$form.Show() はメッセージループなしではデッドロック
    # するため使用しない。
    _PS_FILE = "\n".join([
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8",
        "Add-Type -AssemblyName System.Windows.Forms",
        "[System.Windows.Forms.Application]::EnableVisualStyles()",
        "$script:result=''",
        "$form=New-Object System.Windows.Forms.Form",
        "$form.TopMost=$true",
        "$form.WindowState='Minimized'",
        "$form.ShowInTaskbar=$false",
        "$form.Add_Shown({",
        "  $d=New-Object System.Windows.Forms.OpenFileDialog",
        "  $d.Title='ファイルを選択'",
        "  $d.Filter='テキストファイル (*.txt;*.md;*.csv)|*.txt;*.md;*.csv|すべてのファイル (*.*)|*.*'",
        "  if($d.ShowDialog($form) -eq 'OK'){$script:result=$d.FileName}",
        "  $form.Close()",
        "})",
        "[System.Windows.Forms.Application]::Run($form)",
        "Write-Output $script:result",
    ])

    _PS_FOLDER = "\n".join([
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8",
        "Add-Type -AssemblyName System.Windows.Forms",
        "[System.Windows.Forms.Application]::EnableVisualStyles()",
        "$script:result=''",
        "$form=New-Object System.Windows.Forms.Form",
        "$form.TopMost=$true",
        "$form.WindowState='Minimized'",
        "$form.ShowInTaskbar=$false",
        "$form.Add_Shown({",
        "  $d=New-Object System.Windows.Forms.FolderBrowserDialog",
        "  $d.Description='フォルダを選択'",
        "  if($d.ShowDialog($form) -eq 'OK'){$script:result=$d.SelectedPath}",
        "  $form.Close()",
        "})",
        "[System.Windows.Forms.Application]::Run($form)",
        "Write-Output $script:result",
    ])

    def _run_ps_dialog(script: str) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                timeout=120,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
            return result.stdout.decode("utf-8", errors="replace").strip()
        except subprocess.TimeoutExpired:
            return "__error__:ダイアログがタイムアウトしました"
        except Exception as e:
            return f"__error__:{e}"

    @PromptServer.instance.routes.get("/sfn/browse/file")
    async def sfn_browse_file(request):
        loop = asyncio.get_running_loop()
        path = await loop.run_in_executor(None, lambda: _run_ps_dialog(_PS_FILE))
        if path.startswith("__error__:"):
            return web.json_response({"path": "", "error": path[10:]}, status=500)
        return web.json_response({"path": path})

    @PromptServer.instance.routes.get("/sfn/browse/folder")
    async def sfn_browse_folder(request):
        loop = asyncio.get_running_loop()
        path = await loop.run_in_executor(None, lambda: _run_ps_dialog(_PS_FOLDER))
        if path.startswith("__error__:"):
            return web.json_response({"path": "", "error": path[10:]}, status=500)
        return web.json_response({"path": path})

except Exception as e:
    print(f"[ComfyUI-String-Function] ブラウズAPIを登録できませんでした: {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
