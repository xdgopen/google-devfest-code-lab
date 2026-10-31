import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { buildMessage, ComposeForm, SAMPLE_TOPICS, validateCompose } from "./ComposeForm";

describe("validateCompose", () => {
  const base = { topic: "Docker for local DBs", githubUrl: "", preferences: {} };
  it("accepts valid input", () => expect(validateCompose(base, 100)).toEqual({}));
  it("rejects short / long topics", () => {
    expect(validateCompose({ ...base, topic: "abc" }, 100).topic).toMatch(/ít nhất/);
    expect(validateCompose({ ...base, topic: "x".repeat(101) }, 100).topic).toMatch(/tối đa 100/);
  });
  it("only allows github repository URLs", () => {
    expect(validateCompose({ ...base, githubUrl: "https://evil.com/a/b" }, 100).githubUrl).toBeDefined();
    expect(validateCompose({ ...base, githubUrl: "https://github.com/google/adk-python" }, 100)).toEqual({});
  });
  it("builds the agent message", () => {
    expect(buildMessage({ ...base, githubUrl: " https://github.com/a/b " })).toBe(
      "Docker for local DBs\n\nGitHub repository: https://github.com/a/b",
    );
  });
});

describe("<ComposeForm>", () => {
  it("shows errors and does not submit invalid input", async () => {
    const onSubmit = vi.fn();
    render(<ComposeForm maxChars={200} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: /bắt đầu viết/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("ít nhất 5");
    expect(screen.getByLabelText("Chủ đề")).toHaveAttribute("aria-invalid", "true");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a sample topic with toggled preferences", async () => {
    const onSubmit = vi.fn();
    render(<ComposeForm maxChars={200} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: SAMPLE_TOPICS[1] }));
    const vi_ = screen.getByRole("button", { name: "Vietnamese" });
    await userEvent.click(vi_);
    expect(vi_).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: /Thân thiện/ }));
    await userEvent.click(screen.getByRole("button", { name: /Thân thiện/ })); // toggle off
    await userEvent.click(screen.getByRole("button", { name: /bắt đầu viết/i }));
    expect(onSubmit).toHaveBeenCalledWith(SAMPLE_TOPICS[1], { language: "Vietnamese", tone: undefined });
  });

  it("disables the CTA while running", () => {
    render(<ComposeForm maxChars={200} disabled onSubmit={() => {}} />);
    expect(screen.getByRole("button", { name: /đang viết/i })).toBeDisabled();
  });
});
