import Editor, { loader, type OnMount } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/editor/editor.worker?worker";
import { useRef } from "react";

// Bundle Monaco locally instead of loading it from a CDN.
self.MonacoEnvironment = { getWorker: () => new editorWorker() };
loader.config({ monaco });
// handy for debugging and browser tests in development
if (import.meta.env.DEV) (window as unknown as { __monaco: typeof monaco }).__monaco = monaco;

monaco.editor.defineTheme("coach", {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "keyword", foreground: "9DB4FF" },
    { token: "string", foreground: "F2D17A" },
    { token: "number", foreground: "F2A27A" },
    { token: "comment", foreground: "7D879A", fontStyle: "italic" },
  ],
  colors: {
    "editor.background": "#141A24",
    "editor.lineHighlightBackground": "#1B2330",
    "editorLineNumber.foreground": "#5A6577",
    "editorLineNumber.activeForeground": "#C9D1DE",
    "editor.selectionBackground": "#2B59F066",
  },
});

interface Props {
  value: string;
  onChange: (v: string) => void;
  /** called with the text of every paste, so the page can tell if it came from the assistant */
  onPaste?: (text: string) => void;
  onRun?: () => void;
  readOnly?: boolean;
}

export default function CodeEditor({ value, onChange, onPaste, onRun, readOnly }: Props) {
  const runRef = useRef(onRun);
  runRef.current = onRun;
  const pasteRef = useRef(onPaste);
  pasteRef.current = onPaste;

  const mount: OnMount = (editor, m) => {
    editor.onDidPaste((e) => {
      const text = editor.getModel()?.getValueInRange(e.range) ?? "";
      pasteRef.current?.(text);
    });
    editor.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Enter, () => runRef.current?.());
  };

  return (
    <Editor
      height="100%"
      defaultLanguage="python"
      theme="coach"
      value={value}
      onChange={(v) => onChange(v ?? "")}
      onMount={mount}
      options={{
        readOnly,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 14,
        lineHeight: 22,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        tabSize: 4,
        padding: { top: 14, bottom: 14 },
        renderLineHighlight: "line",
        automaticLayout: true,
        ariaLabel: "Code editor",
      }}
    />
  );
}
