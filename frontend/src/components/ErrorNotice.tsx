interface ErrorNoticeProps {
  readonly message: string;
  readonly onRetry: () => void;
}

/**
 * Error card shown when the backend cannot be reached.
 *
 * The message is deliberately generic: it explains the likely cause (backend
 * not started) without displaying a stack trace or internal path.
 */
export function ErrorNotice({ message, onRetry }: ErrorNoticeProps) {
  return (
    <div className="card card--error" role="alert">
      <h2>Backend unreachable</h2>
      <p>
        The application could not read <code>/health</code> and <code>/version</code> from
        the local FastAPI service.
      </p>
      <p className="muted">{message}</p>
      <ol>
        <li>
          Start the backend:{" "}
          <code>powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1</code>
        </li>
        <li>Confirm it is listening on http://127.0.0.1:8000/health</li>
        <li>Reload this page.</li>
      </ol>
      <button type="button" className="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
