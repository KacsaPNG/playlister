import { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { SongSubmitForm } from "./components/SongSubmitForm";
import { Playlist } from "./components/Playlist";
import { DevLoginModal } from "./components/DevAuth";
import { QrModal } from "./components/QrModal";
import { PlaylistAPI } from "./services/api";
import type { Track, SubmitTrackInput } from "./types";

export function App() {
  const [tracks, setTracks] = useState<Track[]>([]);
  // The website must NOT open in dev view by default:
  const [isDevMode, setIsDevMode] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  // ── Polling ──────────────────────────────────────────────────────────────
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await PlaylistAPI.getPlaylist();
        if (active && res.success) setTracks(res.tracks);
      } catch {
        /* silent */
      }
    };
    poll();
    const t = setInterval(poll, 4000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, []);

  // ── Auth ─────────────────────────────────────────────────────────────────
  const toggleDev = () => {
    if (isDevMode) {
      setIsDevMode(false);
      notify("Kilépve a fejlesztői nézetből");
    } else {
      setShowLogin(true);
    }
  };

  const handleUnlock = () => {
    setIsDevMode(true);
    setShowLogin(false);
    notify("Fejlesztői nézet bekapcsolva");
  };

  // ── Submit ───────────────────────────────────────────────────────────────
  const handleSubmit = async (input: SubmitTrackInput) => {
    setIsSubmitting(true);
    try {
      const res = await PlaylistAPI.submitTrack(input);
      if (res.success) {
        const r2 = await PlaylistAPI.getPlaylist();
        if (r2.success) setTracks(r2.tracks);
      }
      return { success: res.success, error: res.error };
    } catch {
      return { success: false, error: "Hálózati hiba. Kérlek, próbáld újra." };
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Dev actions ──────────────────────────────────────────────────────────
  const refresh = async () => {
    const res = await PlaylistAPI.getPlaylist();
    if (res.success) setTracks(res.tracks);
  };

  const handleRemove = async (id: string) => {
    const t = tracks.find((x) => x.id === id);
    await PlaylistAPI.removeTrack(id);
    await refresh();
    if (t) notify(`"${t.title}" törölve a lejátszási listáról`);
  };

  const handleReorder = async (id: string, direction: "up" | "down") => {
    await PlaylistAPI.reorderTrack(id, direction);
    await refresh();
  };

  const handleClearAll = async () => {
    await PlaylistAPI.clearAllTracks();
    setTracks([]);
    notify("A lejátszási lista kiürítve");
  };

  return (
    <>
      <Header
        isDevMode={isDevMode}
        onToggleDev={toggleDev}
        onOpenQr={() => setShowQr(true)}
        onClearAll={handleClearAll}
      />

      <main className="page">
        <SongSubmitForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />

        <Playlist
          tracks={tracks}
          isDevMode={isDevMode}
          onRemove={handleRemove}
          onReorder={handleReorder}
        />
      </main>

      <DevLoginModal
        isOpen={showLogin}
        onClose={() => setShowLogin(false)}
        onUnlock={handleUnlock}
      />
      <QrModal isOpen={showQr} onClose={() => setShowQr(false)} />

      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </>
  );
}

export default App;
