import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyUI.StringFunction.PromptPreview",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SFn_PromptPreview") return;

        // ノード配置時に初期サイズを確保（ウィジェットがはみ出ないように）
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            this.setSize([400, 280]);
        };

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            onExecuted?.apply(this, arguments);

            const text = message?.text?.[0] ?? "";

            // 初回実行時だけウィジェットを生成
            if (!this._previewWidget) {
                this._previewWidget = ComfyWidgets["STRING"](
                    this,
                    "_preview_display",
                    ["STRING", { multiline: true, default: "" }],
                    app
                ).widget;

                const el = this._previewWidget.inputEl;
                el.readOnly    = true;
                el.style.cssText = `
                    min-height : 180px;
                    font-size  : 11px;
                    line-height: 1.5;
                    resize     : none;
                    opacity    : 0.85;
                    font-family: monospace;
                `;
            }

            this._previewWidget.value = text;

            // ノードサイズをウィジェット内容に合わせて更新
            const sz = this.computeSize();
            if (this.size[1] < sz[1]) {
                this.setSize([this.size[0], sz[1]]);
            }
            app.graph.setDirtyCanvas(true, true);
        };
    },
});
