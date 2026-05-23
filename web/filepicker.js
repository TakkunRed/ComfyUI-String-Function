import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "SFn.FilePicker",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const allInputs = Object.assign(
            {},
            nodeData.input?.required ?? {},
            nodeData.input?.optional ?? {}
        );

        const hasFilePath   = "file_path"   in allInputs;
        const hasFolderPath = "folder_path" in allInputs;
        if (!hasFilePath && !hasFolderPath) return;

        const widgetName = hasFilePath ? "file_path" : "folder_path";
        const endpoint   = hasFolderPath ? "/sfn/browse/folder" : "/sfn/browse/file";
        const label      = hasFolderPath ? "📂 フォルダを参照..." : "📄 ファイルを参照...";

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = origOnNodeCreated?.apply(this, arguments);

            const targetWidget = this.widgets?.find(w => w.name === widgetName);
            if (!targetWidget) return result;

            this.addWidget("button", label, null, async () => {
                let resp;
                try {
                    resp = await fetch(endpoint);
                } catch (e) {
                    alert("[ComfyUI-String-Function]\n接続エラー: ComfyUI サーバーに到達できません。\n" + e.message);
                    return;
                }

                if (!resp.ok) {
                    const body = await resp.json().catch(() => ({}));
                    alert("[ComfyUI-String-Function]\nダイアログを開けませんでした。\n" + (body.error ?? `HTTP ${resp.status}`));
                    return;
                }

                const data = await resp.json();
                if (data.path) {
                    targetWidget.value = data.path;
                    app.graph.setDirtyCanvas(true, true);
                }
            });

            return result;
        };
    },
});
