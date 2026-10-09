"use client";

import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { RichTextEditor } from "@/components/editor/rich-text-editor";
import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  type CurriculumTopic,
  type Subtopic,
} from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

const CONTENT_TYPES = [
  { value: "video", label: "Video" },
  { value: "article", label: "Article" },
  { value: "pdf", label: "PDF" },
  { value: "spreadsheet", label: "Spreadsheet" },
  { value: "document", label: "Word" },
  { value: "presentation", label: "PowerPoint" },
  { value: "audio", label: "Audio" },
  { value: "image", label: "Image" },
  { value: "link", label: "Link / Embed" },
  { value: "live", label: "Live session" },
];

const ITEM_KINDS = [
  { value: "subtopic", label: "Subtopic (lesson)" },
  { value: "quiz", label: "Quiz" },
  { value: "assignment", label: "Assignment" },
  { value: "practice_test", label: "Practice test" },
];

function SortableRow({
  id,
  children,
}: {
  id: string;
  children: (handleProps: Record<string, unknown>) => React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  return (
    <div ref={setNodeRef} style={style}>
      {children({ ...attributes, ...listeners })}
    </div>
  );
}

export default function CurriculumPage() {
  const params = useParams<{ id: string }>();
  const { refresh, markSaved } = useSubjectManage();
  const [topics, setTopics] = useState<CurriculumTopic[]>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Subtopic | null>(null);
  const [newTopic, setNewTopic] = useState("");
  const [draftTitles, setDraftTitles] = useState<Record<string, string>>({});
  const [pickerTopic, setPickerTopic] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const load = useCallback(async () => {
    const tree = await api.getCurriculum(params.id);
    setTopics(tree);
    setExpanded((prev) => {
      const next = { ...prev };
      for (const t of tree) if (next[t.id] === undefined) next[t.id] = true;
      return next;
    });
  }, [params.id]);

  useEffect(() => {
    void load().catch((err: ApiError) => toast.error(err.message));
  }, [load]);

  async function addTopic() {
    if (!newTopic.trim()) return;
    try {
      await api.createTopic(params.id, { title: newTopic.trim() });
      setNewTopic("");
      markSaved();
      await load();
      await refresh();
      toast.success("Topic added");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function onTopicDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = topics.findIndex((t) => t.id === active.id);
    const newIndex = topics.findIndex((t) => t.id === over.id);
    const next = arrayMove(topics, oldIndex, newIndex);
    setTopics(next);
    try {
      await api.reorderTopics(
        params.id,
        next.map((t) => t.id),
      );
      markSaved();
    } catch (err) {
      toast.error((err as ApiError).message);
      await load();
    }
  }

  async function addItem(topicId: string, kind: string) {
    const title = (draftTitles[topicId] ?? "").trim() || `New ${kind.replaceAll("_", " ")}`;
    try {
      await api.createSubtopic(topicId, {
        title,
        kind,
        min_time_s: kind === "subtopic" ? 60 : 0,
      });
      setDraftTitles((p) => ({ ...p, [topicId]: "" }));
      setPickerTopic(null);
      markSaved();
      await load();
      await refresh();
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function openEditor(subId: string) {
    try {
      setEditing(await api.getSubtopic(subId));
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function fetchSubtopic(id: string): Promise<Subtopic> {
    return api.getSubtopic(id);
  }

  async function saveContent(type: string, extra: Record<string, unknown> = {}) {
    if (!editing) return;
    try {
      await api.setSubtopicContent(editing.id, { content_type: type, ...extra });
      markSaved();
      toast.success("Content saved");
      setEditing(await fetchSubtopic(editing.id));
      await load();
      await refresh();
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function onFile(type: string, file: File | null) {
    if (!editing || !file) return;
    try {
      const uploadId = await api.uploadFile(file, "content", editing.id);
      await saveContent(type, { upload_id: uploadId, title: file.name });
    } catch (err) {
      toast.error((err as ApiError).message ?? "Upload failed");
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h2 className="font-display text-2xl">Curriculum</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Build topics and subtopics. Drag to reorder. Add video, docs, articles, and quizzes.
        </p>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => void onTopicDragEnd(e)}>
        <SortableContext items={topics.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-3">
            {topics.map((topic, ti) => (
              <SortableRow key={topic.id} id={topic.id}>
                {(handleProps) => (
                  <section className="rounded-lg border border-[var(--border)] bg-[var(--card)]">
                    <div className="flex items-start gap-2 border-b border-[var(--border)] px-3 py-2">
                      <button
                        type="button"
                        className="mt-1 cursor-grab text-[var(--muted-foreground)]"
                        {...handleProps}
                        aria-label="Drag topic"
                      >
                        <GripVertical className="h-4 w-4" />
                      </button>
                      <div className="min-w-0 flex-1">
                        <button
                          type="button"
                          className="text-left font-medium"
                          onClick={() =>
                            setExpanded((p) => ({ ...p, [topic.id]: !p[topic.id] }))
                          }
                        >
                          Topic {ti + 1}: {topic.title}
                        </button>
                        <Input
                          className="mt-1 h-9"
                          placeholder="What will students be able to do at the end of this topic?"
                          defaultValue={topic.objective_text}
                          onBlur={(e) => {
                            void api
                              .updateTopic(topic.id, { objective_text: e.target.value })
                              .then(() => markSaved())
                              .catch((err: ApiError) => toast.error(err.message));
                          }}
                        />
                      </div>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            void api.duplicateTopic(topic.id).then(load).then(refresh)
                          }
                        >
                          Duplicate
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (!confirm("Delete topic?")) return;
                            void api.deleteTopic(topic.id).then(load).then(refresh);
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>

                    {expanded[topic.id] !== false ? (
                      <div className="space-y-1 p-2">
                        {topic.subtopics.map((sub, si) => (
                          <div
                            key={sub.id}
                            className="flex min-h-11 items-center gap-2 rounded-md px-2 hover:bg-[var(--muted)]/50"
                          >
                            <span className="w-6 text-xs text-[var(--muted-foreground)]">{si + 1}</span>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-medium">{sub.title}</p>
                              <p className="text-xs text-[var(--muted-foreground)]">
                                {sub.kind}
                                {sub.content_type ? ` · ${sub.content_type}` : ""}
                                {sub.estimated_time_s
                                  ? ` · ${Math.round(sub.estimated_time_s / 60)}m`
                                  : ""}
                              </p>
                            </div>
                            {sub.has_content ? (
                              <Badge className="bg-[var(--primary)]/15 text-[var(--primary)]">✓</Badge>
                            ) : (
                              <span className="h-2 w-2 rounded-full bg-[var(--destructive)]" title="Incomplete" />
                            )}
                            <Badge>{sub.is_published ? "Published" : "Draft"}</Badge>
                            <Button size="sm" variant="outline" onClick={() => void openEditor(sub.id)}>
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                if (!confirm("Delete item?")) return;
                                void api.deleteSubtopic(sub.id).then(load).then(refresh);
                              }}
                            >
                              Delete
                            </Button>
                          </div>
                        ))}

                        <div className="flex flex-wrap items-center gap-2 px-2 pt-2">
                          <Input
                            className="h-9 max-w-xs"
                            placeholder="New item title"
                            value={draftTitles[topic.id] ?? ""}
                            onChange={(e) =>
                              setDraftTitles((p) => ({ ...p, [topic.id]: e.target.value }))
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") void addItem(topic.id, "subtopic");
                            }}
                          />
                          <Button size="sm" onClick={() => void addItem(topic.id, "subtopic")}>
                            + Subtopic
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              setPickerTopic(pickerTopic === topic.id ? null : topic.id)
                            }
                          >
                            + Curriculum item
                          </Button>
                        </div>
                        {pickerTopic === topic.id ? (
                          <div className="flex flex-wrap gap-2 px-2 pb-2">
                            {ITEM_KINDS.map((k) => (
                              <Button
                                key={k.value}
                                size="sm"
                                variant="secondary"
                                onClick={() => void addItem(topic.id, k.value)}
                              >
                                {k.label}
                              </Button>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </section>
                )}
              </SortableRow>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="flex gap-2">
        <Input
          placeholder="New topic title"
          value={newTopic}
          onChange={(e) => setNewTopic(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void addTopic();
          }}
        />
        <Button onClick={() => void addTopic()}>
          <Plus className="mr-1 h-4 w-4" /> Topic
        </Button>
      </div>

      {editing ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="max-h-[90dvh] w-full max-w-2xl overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 shadow-lg">
            <div className="mb-4 flex items-start justify-between gap-2">
              <div>
                <h3 className="font-display text-xl">{editing.title}</h3>
                <p className="text-xs text-[var(--muted-foreground)]">{editing.kind}</p>
              </div>
              <Button variant="outline" onClick={() => setEditing(null)}>
                Close
              </Button>
            </div>

            <div className="mb-4 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>Title</Label>
                <Input
                  defaultValue={editing.title}
                  onBlur={(e) => {
                    void api
                      .updateSubtopic(editing.id, { title: e.target.value })
                      .then((s) => {
                        setEditing(s);
                        markSaved();
                        return load();
                      });
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label>Min study time (seconds)</Label>
                <Input
                  type="number"
                  defaultValue={editing.min_time_s}
                  onBlur={(e) => {
                    void api
                      .updateSubtopic(editing.id, { min_time_s: Number(e.target.value) || 0 })
                      .then((s) => {
                        setEditing(s);
                        markSaved();
                      });
                  }}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editing.is_free_preview}
                  onChange={(e) => {
                    void api
                      .updateSubtopic(editing.id, { is_free_preview: e.target.checked })
                      .then((s) => {
                        setEditing(s);
                        markSaved();
                      });
                  }}
                />
                Free preview
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={Boolean(editing.require_full_watch)}
                  onChange={(e) => {
                    void api
                      .updateSubtopic(editing.id, { require_full_watch: e.target.checked })
                      .then((s) => {
                        setEditing(s);
                        markSaved();
                      });
                  }}
                />
                Require full watch
              </label>
            </div>

            <div className="mb-3">
              <Label className="mb-2 block">Add content</Label>
              <div className="flex flex-wrap gap-2">
                {CONTENT_TYPES.map((ct) => (
                  <Button
                    key={ct.value}
                    size="sm"
                    variant={editing.content?.content_type === ct.value ? "default" : "outline"}
                    onClick={() => {
                      if (ct.value === "article") {
                        void saveContent("article", {
                          body_json: editing.content?.body_json ?? { html: "<p></p>" },
                        });
                      } else if (ct.value === "video") {
                        const input = document.createElement("input");
                        input.type = "file";
                        input.accept = "video/*";
                        input.onchange = () => {
                          const file = input.files?.[0];
                          if (!file || !editing) return;
                          void api
                            .uploadVideoToMux(editing.id, file)
                            .then(async () => {
                              markSaved();
                              toast.success("Video uploaded to Mux (processing)");
                              setEditing(await fetchSubtopic(editing.id));
                              await load();
                              await refresh();
                            })
                            .catch((err: ApiError) => toast.error(err.message ?? "Mux upload failed"));
                        };
                        input.click();
                      } else if (ct.value === "link" || ct.value === "live") {
                        const url = window.prompt("URL");
                        if (url) void saveContent(ct.value, { external_url: url });
                      } else {
                        const input = document.createElement("input");
                        input.type = "file";
                        input.onchange = () => void onFile(ct.value, input.files?.[0] ?? null);
                        input.click();
                      }
                    }}
                  >
                    {ct.label}
                  </Button>
                ))}
              </div>
            </div>

            {editing.content?.content_type === "article" ? (
              <div className="mb-4 space-y-2">
                <Label>Article body</Label>
                <RichTextEditor
                  valueHtml={String(editing.content.body_json?.html ?? "<p></p>")}
                  onChange={(html) => {
                    void api
                      .setSubtopicContent(editing.id, {
                        content_type: "article",
                        body_json: { html },
                      })
                      .then((c) => {
                        setEditing({ ...editing, content: c, has_content: true });
                        markSaved();
                      });
                  }}
                />
              </div>
            ) : null}

            {editing.content ? (
              <p className="mb-4 text-xs text-[var(--muted-foreground)]">
                Content: {editing.content.content_type} · {editing.content.processing_status}
                {editing.content.preview_url ? " · preview ready" : ""}
                {editing.content.file_url ? (
                  <>
                    {" · "}
                    <a className="underline" href={editing.content.file_url} target="_blank" rel="noreferrer">
                      file
                    </a>
                  </>
                ) : null}
              </p>
            ) : null}

            <div className="space-y-2">
              <Label>Resources</Label>
              <ul className="space-y-1 text-sm">
                {(editing.resources ?? []).map((r) => (
                  <li key={r.id}>
                    {r.title} ({r.kind})
                  </li>
                ))}
              </ul>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const title = window.prompt("Resource title");
                  const url = window.prompt("URL");
                  if (!title || !url) return;
                  void api
                    .addSubtopicResource(editing.id, { kind: "link", title, url })
                    .then(() => fetchSubtopic(editing.id))
                    .then(setEditing)
                    .then(() => markSaved());
                }}
              >
                Add resource link
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
