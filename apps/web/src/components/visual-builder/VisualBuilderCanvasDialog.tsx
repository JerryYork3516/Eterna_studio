"use client";

import { useEffect, useRef } from "react";

export interface VisualBuilderCanvasDialogState {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm?: () => void;
}

export function VisualBuilderCanvasDialog({
  dialog,
  onCancel,
  onConfirm,
}: {
  dialog: VisualBuilderCanvasDialogState | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!dialog) return;
    confirmButtonRef.current?.focus();
  }, [dialog]);

  if (!dialog) return null;

  return (
    <div
      className="visual-builder-canvas-dialog"
      data-visual-builder-dialog
      onKeyDown={(event) => {
        if (event.key === "Escape" && dialog.cancelLabel) {
          event.preventDefault();
          onCancel();
        }
      }}
    >
      <button
        type="button"
        className="visual-builder-canvas-dialog__backdrop"
        aria-label={dialog.cancelLabel ?? dialog.confirmLabel}
        onClick={dialog.cancelLabel ? onCancel : onConfirm}
      />
      <section
        className="visual-builder-canvas-dialog__window"
        role="dialog"
        aria-modal="true"
        aria-labelledby="visual-builder-dialog-title"
        aria-describedby="visual-builder-dialog-message"
      >
        <header>
          <span aria-hidden="true">◇</span>
          <h2 id="visual-builder-dialog-title">{dialog.title}</h2>
        </header>
        <p id="visual-builder-dialog-message">{dialog.message}</p>
        <footer>
          {dialog.cancelLabel ? (
            <button type="button" onClick={onCancel}>
              {dialog.cancelLabel}
            </button>
          ) : null}
          <button
            ref={confirmButtonRef}
            type="button"
            className={dialog.destructive ? "is-danger" : "is-primary"}
            onClick={onConfirm}
          >
            {dialog.confirmLabel}
          </button>
        </footer>
      </section>
    </div>
  );
}
