"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Archive, ArrowRight, BookmarkCheck, Check, Download, ExternalLink, MessageSquarePlus, NotebookPen, Pencil, Pin, RotateCcw, Search, Target, Upload, X } from "lucide-react";
import type { PlayerMatch } from "@/lib/types";
import { archiveReview, CHECK_LABELS, emptyJournal, followUpMatches, journalKey, mergeJournal, orderedMatches, parseJournal, pinReview, recentSession, recordCheck, REVIEW_TAGS, reviewCandidate, saveReview, sessionHighlight } from "@/lib/review-journal";
import type { MatchMemory, ReviewJournal, ReviewTag } from "@/lib/review-journal";
import styles from "./ReviewJournal.module.css";

export function useReviewJournal(accountId: number) {
  const [loaded, setLoaded] = useState<{ accountId: number; value: ReviewJournal; error: string } | null>(null);
  const [notice, setNotice] = useState("");
  const read = useCallback(() => {
    const raw = window.localStorage.getItem(journalKey(accountId));
    return raw ? parseJournal(raw, accountId) : emptyJournal(accountId);
  }, [accountId]);
  useEffect(() => {
    let active = true;
    const refresh = () => {
      if (!active || !accountId) return;
      try { setLoaded({ accountId, value: read(), error: "" }); }
      catch { setLoaded({ accountId, value: emptyJournal(accountId), error: "复盘本读取失败，原记录未覆盖。可先导出原始备份，再检查存储权限或备份内容。" }); }
      setNotice("");
    };
    const sync = (event: StorageEvent) => { if (event.key === journalKey(accountId) || event.key === null) refresh(); };
    queueMicrotask(refresh);
    window.addEventListener("storage", sync);
    return () => { active = false; window.removeEventListener("storage", sync); };
  }, [accountId, read]);
  const ready = loaded?.accountId === accountId && accountId > 0;
  const state = ready ? loaded.value : emptyJournal(accountId);
  const error = ready ? loaded.error : "";
  const mutate = useCallback((update: (current: ReviewJournal) => ReviewJournal, message = "已保存在此设备") => {
    if (!ready) return false;
    try {
      const value = update(read());
      const raw = JSON.stringify(value);
      parseJournal(raw, accountId);
      window.localStorage.setItem(journalKey(accountId), raw);
      setLoaded({ accountId, value, error: "" });
      setNotice(message);
      return true;
    } catch (cause) {
      const message = cause instanceof Error && cause.name !== "QuotaExceededError" && cause.name !== "SecurityError"
        ? cause.message : "此设备暂时无法保存，可能是存储空间不足或权限受限";
      setNotice(`未保存：${message}`);
      return false;
    }
  }, [accountId, read, ready]);
  function download() {
    try {
      const raw = window.localStorage.getItem(journalKey(accountId)) ?? JSON.stringify(emptyJournal(accountId));
      const url = URL.createObjectURL(new Blob([raw], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `dotasense-${accountId}-reviews.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice("已导出此设备的复盘备份");
    } catch { setNotice("导出失败，请检查浏览器下载权限"); }
  }
  function restore(raw: string) {
    try {
      const backup = parseJournal(raw, accountId);
      return mutate((current) => mergeJournal(current, backup), "备份已合并；已有比赛记录保留本机版本");
    } catch (cause) { setNotice(cause instanceof Error ? cause.message : "备份无法读取"); return false; }
  }
  return { state, ready, error, notice, mutate, download, restore, setNotice };
}
export type JournalController = ReturnType<typeof useReviewJournal>;

function HeroImage({ match }: { match: MatchMemory }) {
  // Hero artwork uses Valve's existing CDN, consistent with match history.
  // eslint-disable-next-line @next/next/no-img-element
  return match.hero_icon ? <img className={styles.hero} src={match.hero_icon} alt="" loading="lazy" /> : <span className={styles.hero} />;
}

export function JournalStatus({ journal }: { journal: JournalController }) {
  if (!journal.notice && !journal.error) return null;
  return <div className={styles.status} role="status">{journal.error || journal.notice}</div>;
}

export function SessionRecap({ matches, journal, loading, onReview, onDetails, onNotebook }: {
  matches: PlayerMatch[]; journal: JournalController; loading: boolean;
  onReview: (match: MatchMemory) => void; onDetails: (match: MatchMemory) => void; onNotebook: () => void;
}) {
  const session = useMemo(() => recentSession(matches), [matches]);
  if (!session.length) return <section className={styles.recap}><h2>最近一组比赛</h2><p className={styles.empty}>暂时没有可回顾的公开比赛。</p></section>;
  const wins = session.filter((match) => match.win).length;
  const unseen = session.filter((match) => !journal.state.seenMatchIds.includes(match.match_id)).length;
  const notes = journal.state.entries.filter((entry) => session.some((match) => match.match_id === entry.match.match_id));
  const candidate = reviewCandidate(session, journal.state.entries);
  const highlight = sessionHighlight(session);
  const oldest = session[session.length - 1];
  const latest = session[0];
  const dates = oldest.played_at.slice(0, 10) === latest.played_at.slice(0, 10)
    ? latest.played_at.slice(0, 10) : `${oldest.played_at.slice(0, 10)} 至 ${latest.played_at.slice(0, 10)}`;
  const minutes = session.every((match) => Number.isFinite(match.duration) && match.duration > 0)
    ? Math.round(session.reduce((sum, match) => sum + match.duration, 0) / 60) : null;
  return <section className={styles.recap} aria-label="最近一组比赛回顾">
    <div className={styles.heading}>
      <div><span className={styles.eyebrow}>{dates}</span><h2>最近一组比赛</h2></div>
      <button className={styles.quietButton} onClick={onNotebook}><NotebookPen size={16} />复盘本<ArrowRight size={14} /></button>
    </div>
    <div className={styles.sessionSummary}>
      <div><strong><span className={styles.win}>{wins} 胜</span><span className={styles.loss}>{session.length - wins} 负</span></strong>
        <span>{session.length} 场{minutes !== null ? ` · 游戏时间 ${minutes} 分钟` : ""} · {notes.length} 条复盘</span></div>
      <span className={styles.badge}>{!journal.ready ? "读取回顾记录" : unseen ? `${unseen} 场待回顾` : "已回顾"}</span>
    </div>
    <div className={styles.sessionMatches} aria-label="这组比赛">
      {[...session].reverse().map((match) => <button key={match.match_id} className={styles.sessionMatch} onClick={() => onReview(match)} aria-label={`记录${match.hero_name}比赛 ${match.match_id}`} disabled={!journal.ready}>
        <HeroImage match={match} /><div><strong>{match.hero_name}</strong><span>{match.kills}/{match.deaths}/{match.assists}</span></div>
        <span className={match.win ? styles.win : styles.loss}>{match.win ? "胜" : "负"}</span>
        {journal.state.entries.some((entry) => entry.match.match_id === match.match_id) && <BookmarkCheck size={14} className={styles.saved} aria-label="已有笔记" />}
      </button>)}
    </div>
    {highlight && <div className={styles.highlight}><div><span className={styles.eyebrow}>本组一个亮点</span><strong>{highlight.match.hero_name}的{highlight.label}达到同英雄 P{highlight.percentile}</strong><p>OpenDota 英雄基准 · 未按你的段位和位置筛选</p></div><button className={styles.quietButton} onClick={() => onDetails(highlight.match)}>看这局<ArrowRight size={14} /></button></div>}
    {candidate ? <div className={styles.candidate}>
      <div><span className={styles.eyebrow}>从这一局开始</span><strong>{candidate.match.hero_name} · {candidate.match.kills}/{candidate.match.deaths}/{candidate.match.assists}</strong>
        <p>{candidate.reason}{loading ? " · 详情补全中" : ""}</p></div>
      <div className={styles.actions}>
        <button className={styles.quietButton} onClick={() => onDetails(candidate.match)}>查看这局<ArrowRight size={14} /></button>
        <button className={styles.primaryButton} disabled={!journal.ready} onClick={() => onReview(candidate.match)}><Pencil size={15} />记一条复盘</button>
      </div>
    </div> : <div className={styles.candidate}><div><strong>这组比赛都有记录了</strong><p>下次再玩，回来看看自己的提醒是否做到了。</p></div><Check size={20} className={styles.win} /></div>}
    <div className={styles.footer}><span title="相邻两场之间的休息不超过 90 分钟，归为同一组；仅包含已加载比赛。">按相邻比赛的休息间隔分组</span>
      <button className={styles.quietButton} disabled={!unseen || !journal.ready} onClick={() => journal.mutate((current) => ({ ...current, seenMatchIds: [...new Set([...current.seenMatchIds, ...session.map((match) => match.match_id)])].slice(-2000) }), "这组比赛已标记为回顾过")}><Check size={14} />{unseen ? "标记已回顾" : "已回顾"}</button></div>
  </section>;
}

export function NextMatchReminder({ journal, matches, onReview }: { journal: JournalController; matches: PlayerMatch[]; onReview: (match: MatchMemory) => void }) {
  const focus = journal.state.entries.find((entry) => entry.match.match_id === journal.state.focusMatchId);
  const eligible = focus ? followUpMatches(focus, matches) : [];
  const pending = eligible.find((match) => !focus?.checks.some((check) => check.matchId === match.match_id));
  const checked = focus?.checks.filter((check) => check.result !== "not_applicable") ?? [];
  return <section className={styles.reminder} aria-label="下局提醒">
    <div className={styles.heading}><h2><Target size={17} />下局只记这一件事</h2>{focus && <button className={styles.iconButton} title="收起提醒，保留复盘记录" aria-label="收起提醒" onClick={() => journal.mutate((current) => ({ ...current, focusMatchId: null }))}><X size={16} /></button>}</div>
    {focus ? <>
      <div className={styles.reminderHero}><HeroImage match={focus.match} /><div><span>下次玩 {focus.match.hero_name}</span><strong>{focus.reminder}</strong></div></div>
      <div className={styles.footer}><span>来自你的复盘 · {focus.tag}</span><button className={styles.iconButton} title="修改提醒" aria-label="修改提醒" onClick={() => onReview(focus.match)}><Pencil size={15} /></button></div>
      {pending ? <div className={styles.checkIn}><strong>这局做到提醒了吗？</strong><span>{pending.played_at} · {pending.kills}/{pending.deaths}/{pending.assists}</span>
        <div className={styles.checkActions}>{(Object.keys(CHECK_LABELS) as (keyof typeof CHECK_LABELS)[]).map((result) => <button key={result} onClick={() => journal.mutate((current) => recordCheck(current, pending, result), "已记录你的执行反馈")} className={styles.quietButton}>{CHECK_LABELS[result]}</button>)}</div>
      </div> : <p className={styles.muted}>{eligible.length ? "已加载的后续同英雄比赛都已反馈" : "等待设置提醒后的同英雄比赛"}</p>}
      {focus.checks.length > 0 && <p className={styles.muted}>自己确认做到 {checked.filter((check) => check.result === "kept").length}/{checked.length} 次 · 不适用 {focus.checks.length - checked.length} 次</p>}
    </> : <div className={styles.empty}><p>还没有下局提醒</p><button className={styles.quietButton} disabled={!matches.length || !journal.ready} onClick={() => { if (matches[0]) onReview(matches[0]); }}><MessageSquarePlus size={15} />从最近一局记起</button></div>}
  </section>;
}

export function ReviewNotebook({ journal, matches, onReview, onDetails }: { journal: JournalController; matches: PlayerMatch[]; onReview: (match: MatchMemory) => void; onDetails: (match: MatchMemory) => void }) {
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"active" | "archived">("active");
  const fileInput = useRef<HTMLInputElement>(null);
  const entries = journal.state.entries.filter((entry) => entry.archived === (view === "archived") && `${entry.match.hero_name} ${entry.match.match_id} ${entry.tag} ${entry.note} ${entry.reminder}`.toLowerCase().includes(query.trim().toLowerCase())).sort((left, right) => right.updatedAt - left.updatedAt);
  return <section className={styles.notebook} aria-label="个人复盘本">
    <div className={styles.heading}><div><span className={styles.eyebrow}>MY DOTA JOURNAL</span><h1>我的复盘本</h1><p className={styles.muted}>此设备保存 · {journal.state.entries.length} 条记录 · 未启用云同步</p></div>
      <div className={styles.actions}>
        <button className={styles.iconButton} title="导出复盘备份" aria-label="导出复盘备份" onClick={journal.download} disabled={!journal.ready}><Download size={18} /></button>
        <button className={styles.iconButton} title="导入备份，只补充缺失的比赛记录" aria-label="导入复盘备份" onClick={() => fileInput.current?.click()} disabled={!journal.ready}><Upload size={18} /></button>
        <input ref={fileInput} className={styles.fileInput} type="file" accept=".json,application/json" aria-label="选择复盘备份" onChange={async (event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          if (file.size > 4_000_000) { journal.setNotice("备份过大，最多支持 4 MB"); return; }
          try { journal.restore(await file.text()); } catch { journal.setNotice("备份文件无法读取"); }
        }} />
      </div>
    </div>
    <JournalStatus journal={journal} />
    <NextMatchReminder journal={journal} matches={matches} onReview={onReview} />
    <div className={styles.notebookToolbar}>
      <label className={styles.search}><Search size={16} /><input aria-label="搜索复盘记录" placeholder="英雄、比赛编号或笔记" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <div className={styles.tabs} aria-label="复盘记录状态"><button aria-pressed={view === "active"} onClick={() => setView("active")}>记录</button><button aria-pressed={view === "archived"} onClick={() => setView("archived")}>归档</button></div>
    </div>
    {!journal.ready ? <p className={styles.empty}>正在读取此设备的复盘本</p> : !entries.length ? <div className={styles.empty}>
      <NotebookPen size={28} /><p>{query ? "没有匹配的复盘记录" : view === "archived" ? "暂无归档记录" : "第一条复盘，从一局真实比赛开始"}</p>
      {view === "active" && !query && <button className={styles.primaryButton} disabled={!matches.length} onClick={() => { if (matches[0]) onReview(matches[0]); }}><Pencil size={15} />记录最近一局</button>}
    </div> : <div className={styles.entries}>{entries.map((entry) => <article key={entry.match.match_id} className={styles.entry}>
      <div className={styles.entryHeader}><HeroImage match={entry.match} /><div><strong>{entry.match.hero_name}</strong><span>{entry.match.played_at} · <span className={entry.match.win ? styles.win : styles.loss}>{entry.match.win ? "胜" : "负"}</span> · {entry.tag}</span></div>
        <div className={styles.entryActions}>
          <button className={styles.iconButton} title="编辑复盘" aria-label={`编辑比赛 ${entry.match.match_id} 的复盘`} onClick={() => onReview(entry.match)}><Pencil size={15} /></button>
          {!entry.archived && entry.reminder && <button className={styles.iconButton} disabled={journal.state.focusMatchId === entry.match.match_id} title={journal.state.focusMatchId === entry.match.match_id ? "当前提醒" : "设为下局提醒（重新开始跟踪）"} aria-label="设为下局提醒" onClick={() => journal.mutate((current) => pinReview(current, entry.match.match_id))}><Pin size={15} /></button>}
          <button className={styles.iconButton} title={entry.archived ? "恢复记录" : "归档记录"} aria-label={entry.archived ? "恢复记录" : "归档记录"} onClick={() => journal.mutate((current) => archiveReview(current, entry.match.match_id))}>{entry.archived ? <RotateCcw size={15} /> : <Archive size={15} />}</button>
        </div>
      </div>
      <p className={styles.noteText}>{entry.note}</p>
      {entry.reminder && <p className={styles.entryReminder}><Target size={14} /><span>{entry.reminder}</span></p>}
      {entry.checks.length > 0 && <details className={styles.feedback}><summary>{entry.checks.length} 条执行反馈 · 玩家自行确认</summary>{entry.checks.map((check) => <div key={check.matchId}><a target="_blank" rel="noreferrer" href={`https://www.opendota.com/matches/${check.matchId}`}>比赛 {check.matchId}</a><span>{CHECK_LABELS[check.result]}</span></div>)}</details>}
      <button className={styles.quietButton} onClick={() => onDetails(entry.match)}>查看比赛证据<ArrowRight size={14} /></button>
    </article>)}</div>}
  </section>;
}

export function ReviewEditor({ match, journal, onClose, onDetails }: { match: MatchMemory; journal: JournalController; onClose: () => void; onDetails: (match: MatchMemory) => void }) {
  const existing = journal.state.entries.find((entry) => entry.match.match_id === match.match_id);
  const [note, setNote] = useState(existing?.note ?? "");
  const [reminder, setReminder] = useState(existing?.reminder ?? "");
  const [tag, setTag] = useState<ReviewTag>(existing?.tag ?? "节奏");
  const initialPin = existing ? journal.state.focusMatchId === match.match_id : true;
  const [pin, setPin] = useState(initialPin);
  const [discardTo, setDiscardTo] = useState<"close" | "details" | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const noteInput = useRef<HTMLTextAreaElement>(null);
  const dirty = note !== (existing?.note ?? "") || reminder !== (existing?.reminder ?? "") || tag !== (existing?.tag ?? "节奏") || pin !== initialPin;
  useEffect(() => { const element = dialog.current; element?.showModal(); noteInput.current?.focus(); return () => element?.close(); }, []);
  const leave = (destination: "close" | "details") => { onClose(); if (destination === "details") onDetails(match); };
  const requestLeave = (destination: "close" | "details") => { if (dirty) setDiscardTo(destination); else leave(destination); };
  return <dialog ref={dialog} className={styles.dialog} aria-labelledby="review-editor-title" onCancel={(event) => { event.preventDefault(); requestLeave("close"); }}>
    <form onSubmit={(event) => { event.preventDefault(); if (journal.mutate((state) => saveReview(state, match, { note, reminder, tag }, pin))) onClose(); }}>
      <div className={styles.heading}><h2 id="review-editor-title">{existing ? "编辑复盘" : "记一条复盘"}</h2><button type="button" className={styles.iconButton} aria-label="关闭复盘编辑" title="关闭" onClick={() => requestLeave("close")}><X size={18} /></button></div>
      {discardTo && <div className={styles.discardPrompt} role="alert"><strong>有尚未保存的修改</strong><div className={styles.actions}><button type="button" className={styles.quietButton} onClick={() => { setDiscardTo(null); noteInput.current?.focus(); }}>继续编辑</button><button type="button" className={styles.quietButton} onClick={() => leave(discardTo)}>放弃修改</button></div></div>}
      <div className={styles.editorMatch}><HeroImage match={match} /><div><strong>{match.hero_name}</strong><span>{match.played_at} · {match.win ? "胜" : "负"}</span></div><a title="在 OpenDota 查看比赛" aria-label="在 OpenDota 查看比赛" target="_blank" rel="noreferrer" className={styles.iconButton} href={`https://www.opendota.com/matches/${match.match_id}`}><ExternalLink size={16} /></a></div>
      <label className={styles.field}>复盘主题<select value={tag} onChange={(event) => setTag(event.target.value as ReviewTag)}>{REVIEW_TAGS.map((value) => <option key={value}>{value}</option>)}</select></label>
      <label className={styles.field}>这局值得记住什么<textarea ref={noteInput} required maxLength={1200} rows={5} value={note} onChange={(event) => setNote(event.target.value)} placeholder="一个做得好的决定，或一个想回看确认的问题" /></label>
      <label className={styles.field}>下次玩这个英雄时提醒我<input maxLength={160} value={reminder} onChange={(event) => setReminder(event.target.value)} placeholder="写成一个自己能执行的动作（选填）" /></label>
      <label className={styles.checkbox}><input type="checkbox" checked={pin && Boolean(reminder.trim())} disabled={!reminder.trim()} onChange={(event) => setPin(event.target.checked)} />设为当前下局提醒{journal.state.focusMatchId && journal.state.focusMatchId !== match.match_id && pin && reminder.trim() && <span>（替换当前提醒，原笔记保留）</span>}</label>
      {existing?.checks.length && existing.reminder !== reminder.trim() ? <p className={styles.muted}>修改提醒会重新开始执行反馈。</p> : null}
      <JournalStatus journal={journal} />
      <div className={styles.editorFooter}><span>此设备保存 · 可在复盘本导出备份</span><button className={styles.primaryButton} disabled={!journal.ready || !note.trim()} type="submit"><Check size={16} />保存复盘</button></div>
      <button type="button" className={styles.quietButton} onClick={() => requestLeave("details")}>先查看比赛证据<ArrowRight size={14} /></button>
    </form>
  </dialog>;
}

export function ReviewHistory({ matches, onReview, journal }: { matches: PlayerMatch[]; onReview: (match: MatchMemory) => void; journal: JournalController }) {
  const [query, setQuery] = useState("");
  const filtered = orderedMatches(matches).filter((match) => `${match.hero_name} ${match.match_id}`.toLowerCase().includes(query.trim().toLowerCase()));
  return <div className={styles.historyActions}>
    <label className={styles.search}><Search size={16} /><input aria-label="查找要复盘的比赛" placeholder="查找英雄或比赛编号" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
    <div className={styles.historyList}>{filtered.map((match) => <button key={match.match_id} className={styles.sessionMatch} onClick={() => onReview(match)} disabled={!journal.ready}><HeroImage match={match} /><div><strong>{match.hero_name}</strong><span>{match.played_at}</span></div><span className={match.win ? styles.win : styles.loss}>{match.win ? "胜" : "负"}</span>{journal.state.entries.some((entry) => entry.match.match_id === match.match_id) ? <BookmarkCheck size={16} /> : <Pencil size={16} />}</button>)}</div>
    {!filtered.length && <p className={styles.empty}>没有找到这场比赛</p>}
  </div>;
}
