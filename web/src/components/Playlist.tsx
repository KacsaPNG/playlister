import React from "react";
import { Music, ExternalLink, Trash2, ArrowUp, ArrowDown } from "lucide-react";
import type { Track } from "../types";

interface PlaylistProps {
  tracks: Track[];
  isDevMode: boolean;
  onRemove: (id: string) => void;
  onReorder: (id: string, direction: "up" | "down") => void;
}

export const Playlist: React.FC<PlaylistProps> = ({
  tracks,
  isDevMode,
  onRemove,
  onReorder,
}) => {
  if (tracks.length === 0) {
    return (
      <div className="card" style={{ padding: "48px 24px", textAlign: "center" }}>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.03)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 12,
          }}
        >
          <Music size={22} color="var(--text-3)" />
        </div>
        <p style={{ color: "var(--text-2)", fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
          A lejátszási lista jelenleg üres
        </p>
        <p style={{ color: "var(--text-3)", fontSize: 13 }}>
          Adj meg egy előadót és egy zenecímet fent az első szám hozzáadásához.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Aktuális lejátszási lista</h2>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "var(--radius-full)",
              background: "rgba(255,255,255,0.06)",
              color: "var(--text-2)",
            }}
          >
            {tracks.length} {tracks.length === 1 ? "szám" : "szám"}
          </span>
        </div>

        {isDevMode && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: "var(--amber)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Fejlesztői nézet: Törlés és átrendezés
          </span>
        )}
      </div>

      <div>
        {tracks.map((track, idx) => {
          const isFirst = idx === 0;
          const isLast = idx === tracks.length - 1;

          return (
            <div key={track.id} className="track-row">
              {/* Position Number */}
              <span
                style={{
                  width: 24,
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--text-3)",
                  textAlign: "center",
                  flexShrink: 0,
                }}
              >
                {idx + 1}
              </span>

              {/* Thumbnail */}
              {track.thumbnailUrl ? (
                <img
                  src={track.thumbnailUrl}
                  alt={`${track.title} borító`}
                  className="track-thumb"
                  loading="lazy"
                />
              ) : (
                <div className="track-thumb-placeholder">
                  <Music size={18} color="var(--text-3)" />
                </div>
              )}

              {/* Track Details */}
              <div className="track-info">
                <div className="track-title" title={track.title}>
                  {track.title}
                </div>
                <div className="track-artist" title={track.artist}>
                  {track.artist}
                </div>
              </div>

              {/* External YouTube Audio Link */}
              {track.url && (
                <a
                  href={track.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-ghost btn-icon"
                  title="Megnyitás a YouTube-on"
                  aria-label="Megnyitás a YouTube-on"
                >
                  <ExternalLink size={14} />
                </a>
              )}

              {/* DEV CONTROLS: Reorder and Remove */}
              {isDevMode && (
                <div style={{ display: "flex", gap: 4, alignItems: "center", marginLeft: 4 }}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-icon"
                    disabled={isFirst}
                    onClick={() => onReorder(track.id, "up")}
                    title="Mozgatás felfelé"
                    aria-label="Mozgatás felfelé"
                  >
                    <ArrowUp size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-icon"
                    disabled={isLast}
                    onClick={() => onReorder(track.id, "down")}
                    title="Mozgatás lefelé"
                    aria-label="Mozgatás lefelé"
                  >
                    <ArrowDown size={14} />
                  </button>

                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => onRemove(track.id)}
                    title="Törlés a lejátszási listáról"
                    aria-label={`${track.title} törlése`}
                  >
                    <Trash2 size={13} />
                    <span>Törlés</span>
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
