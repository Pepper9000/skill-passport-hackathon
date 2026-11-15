import type { Evidence } from "./api";

export function showsNotCountedNote(item: Evidence): boolean {
  return (item.type === "dependency" || item.type === "config") && "authored" in item.checks && !item.checks.authored;
}

/** Stable identity for one cited evidence item, same shape as rejected-claim citation keys. */
export function evidenceCitation(skillId: string, item: { repo: string; file_path: string; start_line: number; end_line: number }): string {
  return `${skillId}:${item.repo}:${item.file_path}:${item.start_line}-${item.end_line}`;
}
