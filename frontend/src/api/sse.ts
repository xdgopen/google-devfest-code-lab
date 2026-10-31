import type { StreamMessage } from "./types";

/** Incremental parser for `data: {...}\n\n` Server-Sent Events frames. */
export function createSseParser(onMessage: (msg: StreamMessage) => void) {
  let buffer = "";
  return (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, "\n");
    let index: number;
    while ((index = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (!data) continue;
      try {
        onMessage(JSON.parse(data) as StreamMessage);
      } catch {
        /* ignore malformed frame */
      }
    }
  };
}
