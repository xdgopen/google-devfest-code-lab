import { useState } from "react";
import { api } from "../api/client";
import type { BlogDetail } from "../api/types";
import { Markdown } from "./Markdown";

type Tab = "post" | "outline" | "extras" | "seo";
const TABS: { id: Tab; label: string }[] = [
  { id: "post", label: "Bài viết" },
  { id: "outline", label: "Dàn ý" },
  { id: "extras", label: "Tiêu đề & Hook" },
  { id: "seo", label: "SEO" },
];

interface Props {
  userId: string;
  result: Pick<BlogDetail, "post" | "outline" | "final" | "seo" | "stats"> & { session_id?: string };
}

export function ResultView({ userId, result }: Props) {
  const [tab, setTab] = useState<Tab>("post");
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.post);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section className="card result" aria-labelledby="result-title">
      <div className="row-between wrap">
        <h2 id="result-title" className="heading">Kết quả</h2>
        <div className="actions">
          <button type="button" className="btn btn--secondary" onClick={copy} disabled={!result.post}>
            {copied ? "✓ Đã copy" : "Copy Markdown"}
          </button>
          {result.session_id && result.post && (
            <>
              <a className="btn btn--secondary" href={api.exportUrl(userId, result.session_id, "md")} download>
                Tải .md
              </a>
              <a className="btn btn--secondary" href={api.exportUrl(userId, result.session_id, "html")} download>
                Tải .html
              </a>
            </>
          )}
        </div>
      </div>

      {result.stats?.word_count ? (
        <p className="meta">
          📝 {result.stats.word_count} từ · ⏱ {result.stats.reading_time_minutes} phút đọc · 💻{" "}
          {result.stats.code_block_count ?? 0} code block
        </p>
      ) : null}

      <div role="tablist" aria-label="Nội dung kết quả" className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            className={`tab ${tab === t.id ? "tab--active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="panel">
        {tab === "post" && (result.post ? <Markdown>{result.post}</Markdown> : <Empty />)}
        {tab === "outline" && (result.outline ? <Markdown>{result.outline}</Markdown> : <Empty />)}
        {tab === "extras" && (result.final ? <Markdown>{result.final}</Markdown> : <Empty />)}
        {tab === "seo" && <SeoPanel seo={result.seo} />}
      </div>
    </section>
  );
}

function Empty() {
  return <p className="empty">Chưa có nội dung.</p>;
}

function SeoPanel({ seo }: { seo: BlogDetail["seo"] }) {
  if (!seo?.slug) return <Empty />;
  return (
    <dl className="seo">
      <dt>Slug</dt>
      <dd><code>{seo.slug}</code></dd>
      <dt>Meta description</dt>
      <dd>{seo.meta_description}</dd>
      <dt>Từ khoá</dt>
      <dd className="chips">{seo.keywords?.map((k) => <span key={k} className="tag">{k}</span>)}</dd>
    </dl>
  );
}
