import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { initialRunState, runReducer } from "../hooks/runReducer";
import { DETAIL, STREAM } from "../test/fixtures";
import { HistoryList } from "./HistoryList";
import { MemoryPanel } from "./MemoryPanel";
import { ProgressTimeline } from "./ProgressTimeline";
import { ResultView } from "./ResultView";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("<ProgressTimeline>", () => {
  it("renders steps with text status (not color only) and retry badge", () => {
    const state = STREAM.slice(0, 4).reduce(
      (s, msg) => runReducer(s, { type: "message", msg }),
      runReducer(initialRunState, { type: "start" }),
    );
    const onCancel = vi.fn();
    render(<ProgressTimeline state={state} onCancel={onCancel} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "33");
    const items = screen.getAllByRole("listitem");
    expect(within(items[0]).getByText("Lập dàn ý")).toBeInTheDocument();
    expect(within(items[0]).getByText("Hoàn tất")).toBeInTheDocument();
    expect(within(items[0]).getByText("↻ 1 lần sửa")).toBeInTheDocument();
    expect(within(items[1]).getByText("Đang chờ")).toBeInTheDocument();
    screen.getByRole("button", { name: "Huỷ" }).click();
    expect(onCancel).toHaveBeenCalled();
  });
});

describe("<ResultView>", () => {
  it("switches tabs and shows export links + stats", async () => {
    render(<ResultView userId="u1" result={DETAIL} />);
    expect(screen.getByText("Agents plan first.")).toBeInTheDocument();
    expect(screen.getByText(/120 từ/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tải .md" })).toHaveAttribute(
      "href", "/api/users/u1/blogs/s1/export?format=md");
    await userEvent.click(screen.getByRole("tab", { name: "SEO" }));
    expect(screen.getByText("planning-loops")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Tiêu đề & Hook" }));
    expect(screen.getByText("Alternate titles")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Dàn ý" }));
    expect(screen.getByRole("tab", { name: "Dàn ý" })).toHaveAttribute("aria-selected", "true");
  });

  it("copies markdown to the clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    render(<ResultView userId="u1" result={DETAIL} />);
    await user.click(screen.getByRole("button", { name: "Copy Markdown" }));
    expect(writeText).toHaveBeenCalledWith(DETAIL.post);
    expect(await screen.findByText("✓ Đã copy")).toBeInTheDocument();
  });

  it("never renders raw HTML from the model", () => {
    const { container } = render(
      <ResultView userId="u1" result={{ ...DETAIL, post: "Hi <img src=x onerror=alert(1)> <script>alert(1)</script>" }} />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });
});

describe("<HistoryList>", () => {
  it("lists, opens and deletes posts", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ items: [DETAIL] }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const onOpen = vi.fn();
    render(<HistoryList userId="u1" onOpen={onOpen} />);
    expect(await screen.findByText("Planning Loops")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Mở" }));
    expect(onOpen).toHaveBeenCalledWith("s1");
    await userEvent.click(screen.getByRole("button", { name: "Xoá Planning Loops" }));
    await waitFor(() => expect(screen.getByText("Chưa có bài nào")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith("/api/users/u1/blogs/s1", { method: "DELETE" });
  });

  it("shows an error state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ detail: "db down" }, 503));
    render(<HistoryList userId="u1" onOpen={() => {}} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("db down");
  });
});

describe("<MemoryPanel>", () => {
  it("shows remembered preferences and recent posts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      preferences: { language: "Vietnamese" },
      post_history: [{ session_id: "s1", title: "Planning Loops", slug: "p", date: "2026-10-31" }],
    }));
    render(<MemoryPanel userId="u1" />);
    expect(await screen.findByText("Planning Loops")).toBeInTheDocument();
    expect(screen.getByText("Ngôn ngữ:")).toBeInTheDocument();
  });

  it("shows empty hints", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ preferences: {}, post_history: [] }));
    render(<MemoryPanel userId="u1" />);
    expect(await screen.findByText(/Chưa có sở thích/)).toBeInTheDocument();
  });
});
