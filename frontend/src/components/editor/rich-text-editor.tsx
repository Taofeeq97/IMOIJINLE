"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  valueHtml?: string;
  onChange: (html: string) => void;
  className?: string;
  placeholder?: string;
};

export function RichTextEditor({ valueHtml = "", onChange, className }: Props) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: valueHtml || "<p></p>",
    immediatelyRender: false,
    onUpdate: ({ editor: ed }) => onChange(ed.getHTML()),
    editorProps: {
      attributes: {
        class:
          "prose prose-sm max-w-none min-h-[140px] px-3 py-2 focus:outline-none text-[var(--foreground)]",
      },
    },
  });

  useEffect(() => {
    if (editor && valueHtml) {
      const current = editor.getHTML();
      if (valueHtml !== current) {
        editor.commands.setContent(valueHtml, { emitUpdate: false });
      }
    }
  }, [valueHtml, editor]);

  if (!editor) return null;

  return (
    <div className={cn("rounded-md border border-[var(--border)] bg-[var(--card)]", className)}>
      <div className="flex flex-wrap gap-1 border-b border-[var(--border)] p-1">
        <Button
          type="button"
          size="sm"
          variant={editor.isActive("bold") ? "default" : "outline"}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          Bold
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor.isActive("italic") ? "default" : "outline"}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          Italic
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor.isActive("bulletList") ? "default" : "outline"}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          List
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor.isActive("heading", { level: 2 }) ? "default" : "outline"}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          H2
        </Button>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
