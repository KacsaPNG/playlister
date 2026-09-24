import React, { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { X, Copy, Check } from "lucide-react";

interface QrModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const QrModal: React.FC<QrModalProps> = ({ isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);
  if (!isOpen) return null;

  const url = window.location.href;

  const copy = () => {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ textAlign: "center" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Megosztás a vendégekkel</h3>
          <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Bezárás">
            <X size={15} />
          </button>
        </div>

        <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 20 }}>
          A vendégek a telefonjukkal beolvashatják ezt a kódot a zenék beküldéséhez.
        </p>

        <div
          style={{
            background: "#fff",
            padding: 16,
            borderRadius: 10,
            display: "inline-block",
            marginBottom: 20,
          }}
        >
          <QRCodeSVG value={url} size={200} level="M" />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <input type="text" readOnly className="input" value={url} style={{ fontSize: 12 }} />
          <button
            type="button"
            className="btn btn-outline"
            onClick={copy}
            style={{ flexShrink: 0 }}
            title="Link másolása"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? "Másolva!" : "Másolás"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
