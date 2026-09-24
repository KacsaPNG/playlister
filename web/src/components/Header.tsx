import React, { useState } from "react";
import { Disc3, QrCode, Shield, LogOut, KeyRound, Trash2 } from "lucide-react";
import { ChangePasswordModal } from "./DevAuth";

interface HeaderProps {
  isDevMode: boolean;
  onToggleDev: () => void;
  onOpenQr: () => void;
  onClearAll: () => void;
}

export const Header: React.FC<HeaderProps> = ({ isDevMode, onToggleDev, onOpenQr, onClearAll }) => {
  const [showChangePassword, setShowChangePassword] = useState(false);

  return (
    <>
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "rgba(9,9,11,0.95)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div
          style={{
            maxWidth: 740,
            margin: "0 auto",
            padding: "0 1rem",
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Disc3 size={20} color="var(--violet)" />
            <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.01em" }}>Playlister</span>
            {isDevMode && (
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  background: "rgba(245,158,11,0.12)",
                  color: "var(--amber)",
                  border: "1px solid rgba(245,158,11,0.25)",
                  padding: "2px 7px",
                  borderRadius: 4,
                }}
              >
                Fejlesztői nézet
              </span>
            )}
          </div>

          {/* Nav actions */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={onOpenQr}
              title="QR-kód megosztása a vendégekkel"
            >
              <QrCode size={14} />
              <span>QR-kód</span>
            </button>

            {isDevMode ? (
              <>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowChangePassword(true)}
                  title="Fejlesztői jelszó módosítása"
                >
                  <KeyRound size={14} />
                  <span>Jelszó módosítása</span>
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => {
                    if (window.confirm("Biztosan törölni szeretnéd az összes zenét a lejátszási listáról?")) {
                      onClearAll();
                    }
                  }}
                  title="Teljes lista törlése"
                >
                  <Trash2 size={14} />
                  <span>Összes törlése</span>
                </button>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={onToggleDev}
                  title="Kilépés a fejlesztői nézetből"
                >
                  <LogOut size={14} />
                  <span>Kilépés</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={onToggleDev}
                title="Belépés a fejlesztői nézetbe"
              >
                <Shield size={14} />
                <span>Fejlesztői nézet</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <ChangePasswordModal
        isOpen={showChangePassword}
        onClose={() => setShowChangePassword(false)}
      />
    </>
  );
};
