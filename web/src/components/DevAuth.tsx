import React, { useState } from "react";
import { KeyRound, X, AlertCircle, Eye, EyeOff, ShieldCheck, Check } from "lucide-react";

const STORAGE_KEY = "playlister_dev_password";
const INITIAL_PASSWORD = "dj2026";

function getStoredPassword(): string {
  return localStorage.getItem(STORAGE_KEY) || INITIAL_PASSWORD;
}

// ── Login modal ──────────────────────────────────────────────────────────────
interface DevLoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUnlock: () => void;
}

export const DevLoginModal: React.FC<DevLoginModalProps> = ({ isOpen, onClose, onUnlock }) => {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === getStoredPassword()) {
      onUnlock();
      setPassword("");
      setError("");
    } else {
      setError("Helytelen jelszó.");
      setPassword("");
    }
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 360 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "rgba(245,158,11,0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <KeyRound size={16} color="var(--amber)" />
            </div>
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Fejlesztői belépés</h3>
          </div>
          <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Bezárás">
            <X size={15} />
          </button>
        </div>

        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 12px",
              borderRadius: 6,
              background: "var(--red-dim)",
              border: "1px solid rgba(239,68,68,0.25)",
              color: "var(--red)",
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label htmlFor="dev-password-input" className="field-label">
            Jelszó
          </label>
          <div style={{ position: "relative", marginBottom: 16 }}>
            <input
              id="dev-password-input"
              type={showPassword ? "text" : "password"}
              className="input"
              placeholder="Add meg a jelszót"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
              autoFocus
              style={{ paddingRight: 40 }}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              style={{
                position: "absolute",
                right: 10,
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--text-3)",
                display: "flex",
                alignItems: "center",
              }}
              aria-label={showPassword ? "Jelszó elrejtése" : "Jelszó megjelenítése"}
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%" }}
            disabled={!password.trim()}
          >
            <ShieldCheck size={15} />
            <span>Belépés</span>
          </button>
        </form>
      </div>
    </div>
  );
};

// ── Change Password modal ────────────────────────────────────────────────────
interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ChangePasswordModal: React.FC<ChangePasswordModalProps> = ({ isOpen, onClose }) => {
  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (current !== getStoredPassword()) {
      setError("A jelenlegi jelszó helytelen.");
      return;
    }
    if (newPass.length < 3) {
      setError("Az új jelszónak legalább 3 karakterből kell állnia.");
      return;
    }
    if (newPass !== confirmPass) {
      setError("Az új jelszavak nem egyeznek.");
      return;
    }

    localStorage.setItem(STORAGE_KEY, newPass);
    setSuccess(true);
    setCurrent("");
    setNewPass("");
    setConfirmPass("");

    setTimeout(() => {
      setSuccess(false);
      onClose();
    }, 1500);
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 360 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
            <KeyRound size={16} color="var(--amber)" />
            Jelszó módosítása
          </h3>
          <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Bezárás">
            <X size={15} />
          </button>
        </div>

        {success ? (
          <div
            style={{
              textAlign: "center",
              padding: "20px 0",
              color: "var(--green)",
              fontWeight: 500,
              fontSize: 14,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
            }}
          >
            <Check size={18} />
            <span>A jelszó sikeresen frissítve!</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label htmlFor="cp-current" className="field-label">
                Jelenlegi jelszó
              </label>
              <input
                id="cp-current"
                type="password"
                className="input"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                autoFocus
                required
              />
            </div>

            <div>
              <label htmlFor="cp-new" className="field-label">
                Új jelszó
              </label>
              <input
                id="cp-new"
                type="password"
                className="input"
                placeholder="Legalább 3 karakter"
                value={newPass}
                onChange={(e) => setNewPass(e.target.value)}
                required
              />
            </div>

            <div>
              <label htmlFor="cp-confirm" className="field-label">
                Új jelszó megerősítése
              </label>
              <input
                id="cp-confirm"
                type="password"
                className="input"
                placeholder="Erősítsd meg az új jelszót"
                value={confirmPass}
                onChange={(e) => setConfirmPass(e.target.value)}
                required
              />
            </div>

            {error && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 12px",
                  borderRadius: 6,
                  background: "var(--red-dim)",
                  border: "1px solid rgba(239,68,68,0.25)",
                  color: "var(--red)",
                  fontSize: 13,
                }}
              >
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              style={{ marginTop: 4 }}
              disabled={!current || !newPass || !confirmPass}
            >
              Új jelszó mentése
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
