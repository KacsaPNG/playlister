import React, { useState } from "react";
import { Music2, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import type { SubmitTrackInput } from "../types";

interface SongSubmitFormProps {
  onSubmit: (data: SubmitTrackInput) => Promise<{ success: boolean; error?: string }>;
  isSubmitting: boolean;
}

export const SongSubmitForm: React.FC<SongSubmitFormProps> = ({ onSubmit, isSubmitting }) => {
  const [artist, setArtist] = useState("");
  const [title, setTitle] = useState("");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !artist.trim()) return;
    setFeedback(null);

    const result = await onSubmit({ title: title.trim(), artist: artist.trim() });
    if (result.success) {
      setArtist("");
      setTitle("");
      setFeedback({ type: "success", msg: "Zene hozzáadva a lejátszási listához!" });
      setTimeout(() => setFeedback(null), 5000);
    } else {
      setFeedback({
        type: "error",
        msg: result.error || "Nem sikerült hozzáadni a zenét. Kérlek, ellenőrizd a címet és az előadót.",
      });
    }
  };

  return (
    <section className="card" style={{ padding: "24px", marginBottom: "16px" }}>
      {/* Title row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: "var(--violet-dim)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Music2 size={16} color="var(--violet)" />
        </div>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.2 }}>Zene beküldése</h2>
          <p style={{ fontSize: 12, color: "var(--text-2)", marginTop: 4 }}>
            A rendszer automatikusan megkeresi a hivatalos audio verziót a YouTube Music-on
          </p>
        </div>
      </div>

      {/* Feedback banner */}
      {feedback && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            marginBottom: 16,
            background: feedback.type === "success" ? "var(--green-dim)" : "var(--red-dim)",
            border: `1px solid ${feedback.type === "success" ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.25)"}`,
            color: feedback.type === "success" ? "var(--green)" : "var(--red)",
            fontSize: 13,
          }}
        >
          {feedback.type === "success" ? (
            <CheckCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
          ) : (
            <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
          )}
          <span>{feedback.msg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
          <div>
            <label htmlFor="song-artist" className="field-label">
              Előadó *
            </label>
            <input
              id="song-artist"
              type="text"
              className="input"
              placeholder="pl. Queen"
              value={artist}
              onChange={(e) => setArtist(e.target.value)}
              required
              autoComplete="off"
            />
          </div>
          <div>
            <label htmlFor="song-title" className="field-label">
              Szám címe *
            </label>
            <input
              id="song-title"
              type="text"
              className="input"
              placeholder="pl. Bohemian Rhapsody"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              autoComplete="off"
            />
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          style={{ width: "100%" }}
          disabled={isSubmitting || !title.trim() || !artist.trim()}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} style={{ animation: "spin 0.6s linear infinite" }} />
              Keresés a YouTube Music-on…
            </>
          ) : (
            "Hozzáadás a lejátszási listához"
          )}
        </button>
      </form>
    </section>
  );
};
